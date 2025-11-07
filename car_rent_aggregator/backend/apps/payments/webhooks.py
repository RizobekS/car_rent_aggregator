# apps/payments/webhooks.py
from __future__ import annotations

import logging
from decimal import Decimal

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from paytechuz.integrations.django.webhooks import (
    PaymeWebhook as BasePaymeWebhookView,
    ClickWebhook as BaseClickWebhookView,
    InvalidAmount,
    AccountNotFound,
)

from apps.bookings.models import Booking
from .models import Payment
from apps.common.choices import PaymentStatus, PaymentMarker

log = logging.getLogger(__name__)


def _last_pending_payment(booking_id: int, provider: str) -> Payment | None:
    """
    Возвращает последний незавершённый платёж по конкретной брони и провайдеру.
    """
    try:
        return (
            Payment.objects
            .filter(booking_id=booking_id, provider=provider, status=PaymentStatus.PENDING)
            .order_by("-id")
            .first()
        )
    except Exception:
        return None


# ─────────────────────────── Payme ───────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(BasePaymeWebhookView):
    """
    Кастомизация для Payme — проверка суммы и обработка статусов.
    """

    def _validate_amount(self, account, received_tiyin: int) -> None:
        """
        Проверка суммы (тийины) против последнего Payment(PENDING, provider='payme').
        """
        booking_id = getattr(account, "id", None)
        if not booking_id:
            raise InvalidAmount("Incorrect amount. Booking id is missing")

        pay = _last_pending_payment(booking_id, provider="payme")
        if not pay or pay.amount is None:
            raise InvalidAmount("Incorrect amount. Expected: pending payment amount is not set")

        expected_tiyin = int(Decimal(pay.amount) * 100)
        received_tiyin = int(Decimal(received_tiyin))

        if expected_tiyin != received_tiyin:
            raise InvalidAmount(f"Incorrect amount. Expected: {expected_tiyin}, received: {received_tiyin}")

    # ✅ эти два метода вызываются после Perform/Cancel транзакции
    def successfully_payment(self, transaction, account):
        """
        Когда Payme подтверждает оплату.
        """
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment(booking_id, provider="payme")
        if pay:
            pay.status = PaymentStatus.PAID
            pay.raw_meta = transaction.raw_data or {}
            pay.save(update_fields=["status", "raw_meta"])
        log.info("✅ Payme: successful payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)

    def cancelled_payment(self, transaction, account):
        """
        Когда Payme отменяет транзакцию.
        """
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment(booking_id, provider="payme")
        if pay:
            pay.status = PaymentStatus.CANCELLED
            pay.raw_meta = transaction.raw_data or {}
            pay.save(update_fields=["status", "raw_meta"])
        log.warning("❌ Payme: cancelled payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)


# ─────────────────────────── Click ───────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class ClickWebhookView(BaseClickWebhookView):
    """
    Расширение базового ClickWebhook:
     - сначала ищет аккаунт (Booking) по merchant_trans_id,
     - сверяет сумму по последнему Payment(PENDING, provider='click'),
     - потом вызывает стандартный PayTechUz flow.
    """

    def post(self, request, **kwargs):
        try:
            params = request.POST.dict()
            click_trans_id = params.get("click_trans_id")
            merchant_trans_id = params.get("merchant_trans_id")
            amount_raw = params.get("amount", "0")

            # 1️⃣ Ищем аккаунт (Booking)
            try:
                account = self._find_account(merchant_trans_id)
            except AccountNotFound:
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "error": -5,
                        "error_note": "User not found",
                    },
                    status=200,
                )

            # 2️⃣ Проверяем сумму
            booking_id = getattr(account, "id", None)
            try:
                received_amount = float(amount_raw)
            except Exception:
                received_amount = 0.0

            pay = _last_pending_payment(booking_id, provider="click")
            if not pay or pay.amount is None:
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "error": -2,
                        "error_note": "Incorrect amount. Pending payment amount not set.",
                    },
                    status=200,
                )

            expected_amount = float(pay.amount)
            if abs(expected_amount - received_amount) > 0.0001:
                return JsonResponse(
                    {
                        "click_trans_id": click_trans_id,
                        "merchant_trans_id": merchant_trans_id,
                        "error": -2,
                        "error_note": f"Incorrect amount. Expected: {expected_amount}, received: {received_amount}",
                    },
                    status=200,
                )

            # 3️⃣ Всё ОК — отдаём управление базовому PayTechUz
            return super().post(request, **kwargs)

        except Exception as e:
            log.exception("Unexpected error in Click webhook: %s", e)
            return JsonResponse({"error": -7, "error_note": "Internal error"}, status=200)

    # ✅ успешная оплата
    def successfully_payment(self, transaction, account):
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment(booking_id, provider="click")
        if pay:
            pay.status = PaymentStatus.PAID
            pay.raw_meta = transaction.raw_data or {}
            pay.save(update_fields=["status", "raw_meta"])
        log.info("✅ Click: successful payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)

    # ❌ отмена платежа
    def cancelled_payment(self, transaction, account):
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment(booking_id, provider="click")
        if pay:
            pay.status = PaymentStatus.CANCELLED
            pay.raw_meta = transaction.raw_data or {}
            pay.save(update_fields=["status", "raw_meta"])
        log.warning("❌ Click: cancelled payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)
