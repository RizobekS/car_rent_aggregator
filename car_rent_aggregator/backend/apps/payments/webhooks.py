# apps/payments/webhooks.py
from __future__ import annotations

from django.conf import settings
from django.db import transaction as db_transaction
from django.http import JsonResponse

from paytechuz.integrations.django.views import (
    BaseClickWebhookView as PTUBaseClickView,
    BasePaymeWebhookView as PTUBasePaymeView,
)
from .models import Payment
from apps.common.choices import PaymentStatus

from apps.bookings.models import Booking


def _get_payment_from_transaction(transaction, provider: str) -> Payment | None:
    """
    PayTechUz хранит в transaction.account ссылку на нашу модель "аккаунта".
    В настройках ты должен был прописать:
      PAYME_ACCOUNT_MODEL = "payments.Payment"
      CLICK_ACCOUNT_MODEL = "payments.Payment"
    или аналогичную конфигурацию через PAYTECHUZ_SETTINGS.

    Тогда transaction.account_id == payment.pk.
    """
    try:
        return Payment.objects.select_related("booking").get(pk=transaction.account_id, provider=provider)
    except Payment.DoesNotExist:
        return None


def _mark_paid(payment: Payment, external_id: str) -> None:
    """
    Обновление Payment + связанного Booking в момент успешной оплаты.
    """
    if payment.status == PaymentStatus.PAID:
        # Уже оплачен – просто выходим, но для PayTech всё равно вернём success.
        return

    with db_transaction.atomic():
        # Обновляем платёж
        payment.status = PaymentStatus.PAID
        # Сохраняем ID транзакции провайдера (чтобы потом не искать по логам ада)
        if payment.provider == "payme":
            payment.payme_id = external_id
        elif payment.provider == "click":
            payment.click_transaction_id = external_id
        payment.save(update_fields=["status", "payme_id", "click_transaction_id", "updated_at"])

        # Обновляем бронирование (только маркер оплаты, статус брони ты уже ведёшь по своей логике)
        booking: Booking = payment.booking
        if hasattr(booking, "payment_marker"):
            # Например: "none" / "partial" / "paid"
            booking.payment_marker = "paid"
            booking.save(update_fields=["payment_marker", "updated_at"])


def _mark_canceled(payment: Payment, external_id: str) -> None:
    """
    Мягкая отмена оплаты: ставим статус CANCELED, но бронирование не трогаем.
    Отмену самой брони ты решаешь бизнес-логикой (через TTL, ручную отмену и т.п.).
    """
    if payment.status in (PaymentStatus.CANCELED, PaymentStatus.PAID):
        return

    with db_transaction.atomic():
        payment.status = PaymentStatus.CANCELED
        if payment.provider == "payme":
            payment.payme_id = external_id
        elif payment.provider == "click":
            payment.click_transaction_id = external_id
        payment.save(update_fields=["status", "payme_id", "click_transaction_id", "updated_at"])


# ---------------- PAYME -----------------


class PaymeWebhookView(PTUBasePaymeView):
    """
    Важно: мы НЕ трогаем post(), валидацию, подписи и т.п.
    Всё это делает BasePaymeWebhookView.

    Мы просто переопределяем "ивенты", которые библиотека вызывает
    в нужный момент.
    """

    def successfully_payment(self, transaction, *args, **kwargs):
        """
        В PayTechUz этот метод вызывается после успешного PerformTransaction
        (когда деньги реально списаны).
        """
        payment = _get_payment_from_transaction(transaction, provider="payme")
        if payment:
            _mark_paid(payment, external_id=str(transaction.payme_transaction_id))

        # MUST: вернуть "успешный" ответ в формате Payme.
        return JsonResponse(self.render_success_output(transaction))

    def cancelled_payment(self, transaction, *args, **kwargs):
        """
        Вызывается, когда Payme отменяет/откатывает транзакцию.
        """
        payment = _get_payment_from_transaction(transaction, provider="payme")
        if payment:
            _mark_canceled(payment, external_id=str(transaction.payme_transaction_id))

        return JsonResponse(self.render_success_output(transaction))


# ---------------- CLICK -----------------


class ClickWebhookView(PTUBaseClickView):
    """
    Аналогично Payme:
      • не переопределяем post()
      • не трогаем verify_sign(), build_click_response(), и т.п.
      • только реагируем на события.
    """

    def successfully_payment(self, transaction, *args, **kwargs):
        """
        В Click этот хук вызывается, когда приходит завершение оплаты.
        """
        payment = _get_payment_from_transaction(transaction, provider="click")
        if payment:
            _mark_paid(payment, external_id=str(transaction.click_trans_id))

        return JsonResponse(self.render_success_output(transaction))

    def cancelled_payment(self, transaction, *args, **kwargs):
        """
        Отмена / отказ по транзакции Click.
        """
        payment = _get_payment_from_transaction(transaction, provider="click")
        if payment:
            _mark_canceled(payment, external_id=str(transaction.click_trans_id))

        return JsonResponse(self.render_success_output(transaction))
