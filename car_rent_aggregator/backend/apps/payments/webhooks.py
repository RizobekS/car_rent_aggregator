# apps/payments/webhooks.py
from decimal import Decimal
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from paytechuz.integrations.django.webhooks import (
    PaymeWebhook as BasePaymeWebhookView,
    ClickWebhook as BaseClickWebhookView,
)
from paytechuz.core.exceptions import InvalidAmount, AccountNotFound

from apps.bookings.models import Booking
from .models import Payment
from apps.common.choices import PaymentStatus, PaymentMarker


def _last_pending_payment(booking_id: int, provider: str | None = None) -> Payment | None:
    qs = Payment.objects.filter(booking_id=booking_id, status=PaymentStatus.PENDING)
    if provider:
        qs = qs.filter(provider=provider)
    return qs.order_by("-created_at").first()


# ───────── Payme ─────────
@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(BasePaymeWebhookView):
    """
    Минимальный кастом под PayTechUz:
    - сумму валидируем по последнему Payment(PENDING) (аванс/полная)
    - при расхождении кидаем InvalidAmount (=> -31001), при отсутствии платежа — AccountNotFound (=> -31050)
    В остальном поведение оставляем как в библиотеке.
    """

    def _validate_amount(self, account, amount):
        """
        account: Booking (ACCOUNT_MODEL)
        amount: int (тийины) из Payme
        """
        payment = _last_pending_payment(account.id, provider="payme")
        if not payment or payment.amount is None:
            # платёж не инициализирован на нашей стороне -> запрещаем
            raise AccountNotFound("Payment is not initialized for this account")

        expected_tiyin = int(Decimal(payment.amount) * 100)
        received_tiyin = int(Decimal(amount))
        if expected_tiyin != received_tiyin:
            # вернётся -31001 (а не -32400)
            raise InvalidAmount(
                f"Invalid amount. Expected: {expected_tiyin}, received: {received_tiyin}"
            )
        return True

    @transaction.atomic
    def successfully_payment(self, params, transaction_obj):
        booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
        p = _last_pending_payment(booking.id, provider="payme")
        if p:
            p.status = PaymentStatus.PAID
            p.raw_meta = {"payme": {"transaction": transaction_obj.__dict__, "params": params}}
            p.save(update_fields=["status", "raw_meta", "updated_at"])
        booking.payment_marker = PaymentMarker.PAID
        booking.save(update_fields=["payment_marker", "updated_at"])

    @transaction.atomic
    def cancelled_payment(self, params, transaction_obj):
        # вызовется и при CancelTransaction, и при неуспешном завершении
        booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
        p = _last_pending_payment(booking.id, provider="payme")
        if p:
            p.status = PaymentStatus.FAILED
            p.raw_meta = {"payme": {"transaction": transaction_obj.__dict__, "params": params}}
            p.save(update_fields=["status", "raw_meta", "updated_at"])
        # машину освобождать должен ваш слой бронирований (вы это уже добавляли в авто-отмену)


# ───────── Click ─────────
@method_decorator(csrf_exempt, name="dispatch")
class ClickWebhookView(BaseClickWebhookView):
    @transaction.atomic
    def successfully_payment(self, params, transaction_obj):
        booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
        p = _last_pending_payment(booking.id, provider="click")
        if p:
            p.status = PaymentStatus.PAID
            p.raw_meta = {"click": {"transaction": transaction_obj.__dict__, "params": params}}
            p.save(update_fields=["status", "raw_meta", "updated_at"])
        booking.payment_marker = PaymentMarker.PAID
        booking.save(update_fields=["payment_marker", "updated_at"])

    @transaction.atomic
    def cancelled_payment(self, params, transaction_obj):
        booking = Booking.objects.select_for_update().get(id=transaction_obj.account_id)
        p = _last_pending_payment(booking.id, provider="click")
        if p:
            p.status = PaymentStatus.FAILED
            p.raw_meta = {"click": {"transaction": transaction_obj.__dict__, "params": params}}
            p.save(update_fields=["status", "raw_meta", "updated_at"])
