# apps/payments/webhooks.py
from decimal import Decimal
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging

from paytechuz.integrations.django.webhooks import (
    PaymeWebhook as BasePaymeWebhookView,
    ClickWebhook as BaseClickWebhookView,
)
from paytechuz.core.exceptions import InvalidAmount, AccountNotFound

from apps.bookings.models import Booking
from .models import Payment
from apps.common.choices import PaymentStatus, PaymentMarker

log = logging.getLogger(__name__)

def _last_pending_payment(booking_id: int, provider: str | None = None) -> Payment | None:
    qs = Payment.objects.filter(booking_id=booking_id, status=PaymentStatus.PENDING)
    if provider:
        qs = qs.filter(provider=provider)
    return qs.order_by("-created_at").first()

@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(BasePaymeWebhookView):
    """
    Валидация суммы — по последнему Payment(PENDING) (аванс/полная).
    Любые наши побочные действия при success/cancel — идемпотентны,
    ошибки логируем, наружу не отдаём (иначе Payme видит -32400).
    """

    def _validate_amount(self, account, amount):
        p = _last_pending_payment(account.id, provider="payme")
        if not p or p.amount is None:
            raise AccountNotFound("Payment is not initialized for this account")

        expected_tiyin = int(Decimal(p.amount) * 100)
        received_tiyin = int(Decimal(amount))
        if expected_tiyin != received_tiyin:
            raise InvalidAmount(
                f"Invalid amount. Expected: {expected_tiyin}, received: {received_tiyin}"
            )
        return True

    @transaction.atomic
    def successfully_payment(self, params, transaction_obj):
        """
        PayTechUZ уже перевёл транзакцию в state=2.
        Делаем наши апдейты безопасно и идемпотентно.
        """
        try:
            booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)

            # если уже оплачен — тихо выходим
            already_paid = Payment.objects.filter(
                booking_id=booking.id, provider="payme", status=PaymentStatus.PAID
            ).exists()
            if already_paid:
                return

            p = _last_pending_payment(booking.id, provider="payme")
            if p:
                p.status = PaymentStatus.PAID
                meta = p.raw_meta or {}
                meta.setdefault("payme", {})
                meta["payme"]["transaction"] = {
                    "id": transaction_obj.transaction_id,
                    "account_id": transaction_obj.account_id,
                    "state": transaction_obj.state,
                }
                meta["payme"]["params"] = params
                p.raw_meta = meta
                p.save(update_fields=["status", "raw_meta", "updated_at"])

            booking.payment_marker = PaymentMarker.PAID
            booking.save(update_fields=["payment_marker", "updated_at"])

        except Exception as e:
            # не ломаем ответ Payme — только логируем
            log.exception("Payme successfully_payment hook failed: %s", e)

    @transaction.atomic
    def cancelled_payment(self, params, transaction_obj):
        try:
            booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
            # если уже зафиксирован как FAILED/PAID — выходим
            done = Payment.objects.filter(
                booking_id=booking.id, provider="payme",
                status__in=[PaymentStatus.PAID, PaymentStatus.FAILED]
            ).exists()
            if done:
                return

            p = _last_pending_payment(booking.id, provider="payme")
            if p:
                p.status = PaymentStatus.FAILED
                meta = p.raw_meta or {}
                meta.setdefault("payme", {})
                meta["payme"]["transaction"] = {
                    "id": transaction_obj.transaction_id,
                    "account_id": transaction_obj.account_id,
                    "state": transaction_obj.state,
                }
                meta["payme"]["params"] = params
                p.raw_meta = meta
                p.save(update_fields=["status", "raw_meta", "updated_at"])
        except Exception as e:
            log.exception("Payme cancelled_payment hook failed: %s", e)


@method_decorator(csrf_exempt, name="dispatch")
class ClickWebhookView(BaseClickWebhookView):
    @transaction.atomic
    def successfully_payment(self, params, transaction_obj):
        try:
            booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
            already_paid = Payment.objects.filter(
                booking_id=booking.id, provider="click", status=PaymentStatus.PAID
            ).exists()
            if already_paid:
                return

            p = _last_pending_payment(booking.id, provider="click")
            if p:
                p.status = PaymentStatus.PAID
                meta = p.raw_meta or {}
                meta.setdefault("click", {})
                meta["click"]["transaction"] = {
                    "id": transaction_obj.transaction_id,
                    "account_id": transaction_obj.account_id,
                    "state": transaction_obj.state,
                }
                meta["click"]["params"] = params
                p.raw_meta = meta
                p.save(update_fields=["status", "raw_meta", "updated_at"])

            booking.payment_marker = PaymentMarker.PAID
            booking.save(update_fields=["payment_marker", "updated_at"])
        except Exception as e:
            log.exception("Click successfully_payment hook failed: %s", e)

    @transaction.atomic
    def cancelled_payment(self, params, transaction_obj):
        try:
            booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
            done = Payment.objects.filter(
                booking_id=booking.id, provider="click",
                status__in=[PaymentStatus.PAID, PaymentStatus.FAILED]
            ).exists()
            if done:
                return

            p = _last_pending_payment(booking.id, provider="click")
            if p:
                p.status = PaymentStatus.FAILED
                meta = p.raw_meta or {}
                meta.setdefault("click", {})
                meta["click"]["transaction"] = {
                    "id": transaction_obj.transaction_id,
                    "account_id": transaction_obj.account_id,
                    "state": transaction_obj.state,
                }
                meta["click"]["params"] = params
                p.raw_meta = meta
                p.save(update_fields=["status", "raw_meta", "updated_at"])
        except Exception as e:
            log.exception("Click cancelled_payment hook failed: %s", e)
