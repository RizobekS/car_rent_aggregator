# apps/payments/webhooks.py
from __future__ import annotations

import json
import logging
from django.http import JsonResponse, HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from paytechuz.integrations.django.views import (
    BaseClickWebhookView as PTUBaseClickView,
    BasePaymeWebhookView as PTUBasePaymeView,
)

from apps.common.choices import PaymentStatus
from .models import Payment

logger = logging.getLogger(__name__)


def _parse_params(request: HttpRequest) -> dict:
    """
    Click присылает form-urlencoded. Для локальных тестов поддерживаем JSON.
    """
    if request.content_type and "application/json" in request.content_type.lower():
        try:
            return json.loads(request.body.decode("utf-8")) or {}
        except Exception:
            return {}
    return request.POST.dict() if request.method == "POST" else {}


@method_decorator(csrf_exempt, name="dispatch")
class PaymeWebhookView(PTUBasePaymeView):
    """
    Payme webhook: обновляем Payment + Booking.
    """

    def successfully_payment(self, params, transaction):
        try:
            payment_id = transaction.account_id  # мы кладём id Payment в account_id
            pay: Payment = Payment.objects.select_related("booking").get(pk=payment_id)

            pay.status = PaymentStatus.PAID
            pay.provider_ref = str(transaction.transaction_id)
            raw = pay.raw_provider_response or {}
            raw["payme_success"] = {"params": params}
            pay.raw_provider_response = raw
            pay.save(update_fields=["status", "provider_ref", "raw_provider_response"])

            if pay.booking_id:
                pay.booking.mark_paid_by_payment(pay)
        except Payment.DoesNotExist:
            logger.error("Payme: Payment %s not found on success", transaction.account_id)
        except Exception as e:
            logger.exception("Payme successfully_payment handler failed: %s", e)

    def cancelled_payment(self, params, transaction):
        try:
            payment_id = transaction.account_id
            pay: Payment = Payment.objects.select_related("booking").get(pk=payment_id)

            pay.status = PaymentStatus.FAILED
            raw = pay.raw_provider_response or {}
            raw["payme_canceled"] = {"params": params}
            pay.raw_provider_response = raw
            pay.save(update_fields=["status", "raw_provider_response"])

            if pay.booking_id:
                pay.booking.mark_payment_failed(pay)
        except Payment.DoesNotExist:
            logger.error("Payme: Payment %s not found on cancel", transaction.account_id)
        except Exception as e:
            logger.exception("Payme cancelled_payment handler failed: %s", e)


@method_decorator(csrf_exempt, name="dispatch")
class ClickWebhookView(PTUBaseClickView):
    """
    Click webhook: синхронизируемся с нашей моделью Payment и Booking.
    """

    def post(self, request: HttpRequest, **kwargs):
        # Чтобы JSON тоже работал (локальные тесты)
        params = _parse_params(request)
        request.POST = request.POST.copy()
        for k, v in params.items():
            request.POST[k] = v
        return super().post(request, **kwargs)

    def _get_payment(self, merchant_trans_id: str | int) -> Payment | None:
        try:
            return Payment.objects.select_related("booking").get(pk=int(merchant_trans_id))
        except Exception:
            logger.error("Click: Payment %s not found", merchant_trans_id)
            return None

    def transaction_created(self, params, transaction, account):
        """
        Prepare прошёл: сохраним «чёрновик» в raw_provider_response.
        """
        try:
            pay = self._get_payment(params.get("merchant_trans_id"))
            if not pay:
                return
            raw = pay.raw_provider_response or {}
            raw["click_prepare"] = {
                "params": params,
                "transaction_id": transaction.transaction_id,
            }
            pay.raw_provider_response = raw
            pay.save(update_fields=["raw_provider_response"])
        except Exception as e:
            logger.exception("Click transaction_created handler failed: %s", e)

    def successfully_payment(self, params, transaction):
        """
        Complete успешный: Payment.PAID + сообщаем Booking, что оплачен.
        """
        try:
            merchant_trans_id = params.get("merchant_trans_id") or transaction.account_id
            pay = self._get_payment(merchant_trans_id)
            if not pay:
                return

            pay.status = PaymentStatus.PAID
            pay.provider_ref = str(transaction.transaction_id)
            raw = pay.raw_provider_response or {}
            raw["click_complete"] = {"result": "success", "params": params}
            pay.raw_provider_response = raw
            pay.save(update_fields=["status", "provider_ref", "raw_provider_response"])

            if pay.booking_id:
                pay.booking.mark_paid_by_payment(pay)
        except Exception as e:
            logger.exception("Click successfully_payment handler failed: %s", e)

    def cancelled_payment(self, params, transaction):
        """
        Complete с ошибкой: CANCELED + отмена брони (если нужно).
        """
        try:
            merchant_trans_id = params.get("merchant_trans_id") or transaction.account_id
            pay = self._get_payment(merchant_trans_id)
            if not pay:
                return

            pay.status = PaymentStatus.FAILED
            raw = pay.raw_provider_response or {}
            raw["click_complete"] = {"result": "canceled", "params": params}
            pay.raw_provider_response = raw
            pay.save(update_fields=["status", "raw_provider_response"])

            if pay.booking_id:
                pay.booking.mark_payment_failed(pay)
        except Exception as e:
            logger.exception("Click cancelled_payment handler failed: %s", e)
