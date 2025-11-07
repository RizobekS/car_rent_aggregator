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
)

from apps.bookings.models import Booking
from .models import Payment
from apps.common.choices import PaymentStatus, PaymentMarker

log = logging.getLogger(__name__)


# ────────────────────────── helpers ──────────────────────────

def _last_pending_payment_for_booking(booking_id: int, provider: str) -> Payment | None:
    """Последний незавершённый платёж по брони и провайдеру."""
    return (
        Payment.objects
        .filter(booking_id=booking_id, provider=provider, status=PaymentStatus.PENDING)
        .order_by("-id")
        .first()
    )


def _mark_booking_paid(payment: Payment) -> None:
    """Пометить бронь оплаченной, если связана с платежом."""
    try:
        if payment.booking:
            # если у вас есть явные поля/статусы — обновите здесь
            # пример: payment.booking.payment_marker = "paid"
            payment.booking.payment_marker = "paid"
            payment.booking.save(update_fields=["payment_marker"])
    except Exception as e:
        log.warning("Failed to mark booking paid (payment %s): %s", payment.id, e)


def _mark_booking_unpaid(payment: Payment) -> None:
    """Снять флаги оплаты у брони при отмене платежа (если нужно)."""
    try:
        if payment.booking:
            # пример: payment.booking.payment_marker = "unpaid"
            payment.booking.payment_marker = "unpaid"
            payment.booking.save(update_fields=["payment_marker"])
    except Exception as e:
        log.warning("Failed to mark booking unpaid (payment %s): %s", payment.id, e)


# ────────────────────────── PAYME ──────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(BasePaymeWebhookView):
    """
    Кастомизация Payme:
      - валидируем сумму по последнему Payment(PENDING, provider='payme') в тийинах,
      - подтверждаем/отменяем платёж и обновляем бронь.
    """

    def _validate_amount(self, account, received_tiyin: int) -> None:
        """
        Вызывается базовым классом при CheckPerform/Create/Perform.
        account — это Booking (так как ACCOUNT_MODEL = Booking).
        """
        booking_id = getattr(account, "id", None)
        if not booking_id:
            raise InvalidAmount("Incorrect amount. Booking id is missing")

        pay = _last_pending_payment_for_booking(booking_id, provider="payme")
        if not pay or pay.amount is None:
            raise InvalidAmount("Incorrect amount. Pending payment amount is not set")

        expected_tiyin = int(Decimal(pay.amount) * 100)  # суммы Payme — в тийинах
        received_tiyin = int(Decimal(received_tiyin))

        if expected_tiyin != received_tiyin:
            raise InvalidAmount(f"Incorrect amount. Expected: {expected_tiyin}, received: {received_tiyin}")

    # Документация PayTechUz: эти методы вызываются на финальных шагах
    def successfully_payment(self, transaction, account):
        """
        Подтверждённая оплата Payme.
        """
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment_for_booking(booking_id, provider="payme")
        if pay:
            pay.status = PaymentStatus.PAID
            pay.raw_meta = (pay.raw_meta or {}) | {"payme": transaction.raw_data or {}}
            pay.save(update_fields=["status", "raw_meta"])
            _mark_booking_paid(pay)

        log.info("✅ Payme: successful payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)

    def cancelled_payment(self, transaction, account):
        """
        Отменённая оплата Payme.
        """
        booking_id = getattr(account, "id", None)
        pay = _last_pending_payment_for_booking(booking_id, provider="payme")
        if pay:
            pay.status = PaymentStatus.CANCELLED
            pay.raw_meta = (pay.raw_meta or {}) | {"payme": transaction.raw_data or {}}
            pay.save(update_fields=["status", "raw_meta"])
            _mark_booking_unpaid(pay)

        log.warning("❌ Payme: cancelled payment for booking %s", booking_id)
        return JsonResponse(self.response_success(transaction), status=200)


# ─────────────────────────── Click ───────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class ClickWebhookView(BaseClickWebhookView):
    """
    Обработчик Click:
      - ACCOUNT_MODEL указывает на Payment,
      - базовый класс PayTechUz сверяет сумму по Payment.amount,
      - мы только помечаем статусы Payment и обновляем связанную бронь.
    """

    def successfully_payment(self, transaction, account):
        """
        account — это Payment (ACCOUNT_MODEL = apps.payments.models.Payment).
        """
        try:
            payment: Payment = account
            payment.status = PaymentStatus.PAID
            payment.raw_meta = (payment.raw_meta or {}) | {"click": transaction.raw_data or {}}
            payment.save(update_fields=["status", "raw_meta"])
            _mark_booking_paid(payment)
            log.info("✅ Click: successful payment for payment=%s booking=%s",
                     payment.id, getattr(payment.booking, "id", None))
        except Exception as e:
            log.exception("Click successfully_payment error: %s", e)

        # стандартный успешный ответ Click
        return JsonResponse(self.response_success(transaction), status=200)

    def cancelled_payment(self, transaction, account):
        """
        Отмена Click.
        """
        try:
            payment: Payment = account
            payment.status = PaymentStatus.CANCELLED
            payment.raw_meta = (payment.raw_meta or {}) | {"click": transaction.raw_data or {}}
            payment.save(update_fields=["status", "raw_meta"])
            _mark_booking_unpaid(payment)
            log.warning("❌ Click: cancelled payment for payment=%s booking=%s",
                        payment.id, getattr(payment.booking, "id", None))
        except Exception as e:
            log.exception("Click cancelled_payment error: %s", e)

        return JsonResponse(self.response_success(transaction), status=200)
