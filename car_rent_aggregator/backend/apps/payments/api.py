# apps/payments/api.py
from django.urls import reverse
from paytechuz.gateways.payme import PaymeGateway
from paytechuz.gateways.click import ClickGateway
from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from apps.common.permissions import BotOnlyPermission
from .models import Payment
from apps.bookings.models import Booking
from apps.common.choices import PaymentProvider, PaymentStatus
import logging

log = logging.getLogger(__name__)

class PaymentCreateSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Payment
        fields = ("id","booking_id","provider","amount","currency","invoice_id","pay_url","status","raw_meta")
        read_only_fields = ("id","invoice_id","pay_url","status","raw_meta")

    def validate(self, attrs):
        if attrs["provider"] not in (PaymentProvider.CLICK, PaymentProvider.PAYME):
            raise serializers.ValidationError(_("Неверный провайдер оплаты."))
        if attrs["amount"] is None or int(attrs["amount"]) <= 0:
            raise serializers.ValidationError(_("Сумма должна быть больше нуля."))
        return attrs

    def create(self, validated):
        booking = Booking.objects.get(pk=validated.pop("booking_id"))
        provider = validated["provider"]

        # 1) находим или создаём платёж
        payment, _ = Payment.objects.get_or_create(
            booking=booking,
            defaults={
                "status": PaymentStatus.PENDING,
                "amount": validated["amount"],
                "currency": validated.get("currency", "UZS"),
                "provider": provider,
            },
        )

        # если был, обновим сумму/провайдера
        if payment.status != PaymentStatus.PAID:
            payment.amount = validated["amount"]
            payment.provider = provider
            payment.status = PaymentStatus.PENDING
            payment.save(update_fields=["amount", "provider", "status"])

        # 2) генерим invoice_id
        ts = int(timezone.now().timestamp())
        invoice_id = f"{provider}-{payment.pk}-{ts}"

        # 3) теперь ID уже есть → формируем ссылку
        real_url = ""
        raw_meta = payment.raw_meta or {}

        try:
            if provider == PaymentProvider.CLICK:
                cfg = settings.PAYTECHUZ["CLICK"]
                gw = ClickGateway(
                    service_id=cfg["SERVICE_ID"],
                    merchant_id=cfg["MERCHANT_ID"],
                    merchant_user_id=cfg["MERCHANT_USER_ID"],
                    secret_key=cfg["SECRET_KEY"],
                    is_test_mode=cfg["IS_TEST_MODE"],
                )
                # ✅ передаём ID платежа, а не брони
                res = gw.create_payment(
                    id=payment.id,
                    amount=int(validated["amount"]),
                    return_url=settings.BOT_PAY_RETURN_URL,
                )
                raw_meta.update({"click_create": res} if isinstance(res, dict) else {})
                real_url = (res.get("payment_url") if isinstance(res, dict) else str(res or "")) or ""

            elif provider == PaymentProvider.PAYME:
                cfg = settings.PAYTECHUZ["PAYME"]
                gw = PaymeGateway(
                    payme_id=cfg["PAYME_ID"],
                    payme_key=cfg["PAYME_KEY"],
                    is_test_mode=cfg["IS_TEST_MODE"],
                )
                res = gw.create_payment(
                    id=payment.id,
                    amount=int(payment.amount) * 100,  # amount в тиынах
                    return_url=settings.BOT_PAY_RETURN_URL,
                )
                raw_meta.update({"payme_create": res} if isinstance(res, dict) else {})
                real_url = (
                               (res.get("payment_url") or res.get("link", "")) if isinstance(res, dict)
                               else str(res or "")
                           ) or ""
        except Exception as e:
            log.exception("create_payment failed for %s (booking=%s): %s", provider, booking.id, e)
            raw_meta["error"] = str(e)
            real_url = ""

        # 4) сохраняем всё
        payment.invoice_id = invoice_id
        payment.raw_meta = {"provider_url": real_url, **(raw_meta or {})}
        payment.pay_url = ""
        payment.save(update_fields=["invoice_id", "raw_meta", "pay_url"])

        return payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class PaymentViewSet(viewsets.GenericViewSet):
    queryset = Payment.objects.select_related("booking")
    serializer_class = PaymentSerializer
    # permission_classes = (BotOnlyPermission,)

    def create(self, request, *args, **kwargs):
        ser = PaymentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payment = ser.save()

        # короткая ссылка-редирект
        short_url = request.build_absolute_uri(
            reverse("payment_redirect", args=[payment.invoice_id])
        )
        payment.pay_url = short_url[:1024]
        payment.save(update_fields=["pay_url", "updated_at"])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
