# apps/bookings/api.py
from datetime import timedelta
from decimal import Decimal

from rest_framework import serializers, viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.common.permissions import BotOnlyPermission
from apps.common.overlaps import qs_overlaps, fresh_pending

from .models import Booking
from apps.cars.models import Car, CarCalendar
from apps.partners.models import PartnerUser
from apps.users.models import BotUser

from apps.common.choices import BookingStatus, PaymentMarker

HOLD_MINUTES = 20  # TTL ожидания подтверждения


# ---------- helpers ----------
def estimate_quote(car: Car, start, end) -> Decimal:
    """
    Считает сумму аренды от start (включительно) до end (исключая end).
    Будни -> price_weekday, СБ/ВС -> price_weekend (если пусто — берём weekday).
    """
    total = Decimal("0")
    cur = start
    pw = car.price_weekday or Decimal("0")
    we = car.price_weekend or pw
    while cur.date() < end.date():
        total += we if cur.weekday() >= 5 else pw
        cur += timedelta(days=1)
    return total


# ---------- Serializers ----------

class BookingCreateSerializer(serializers.ModelSerializer):
    car_id = serializers.IntegerField(write_only=True)
    client_tg_user_id = serializers.IntegerField(write_only=True)
    # телефон опционально
    client_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # ❗ quote больше не обязателен — если его нет, посчитаем на бэкенде
    price_quote = serializers.DecimalField(
        required=False, allow_null=True, max_digits=12, decimal_places=2
    )

    class Meta:
        model = Booking
        fields = (
            "id",
            "car_id", "client_tg_user_id", "client_phone",
            "date_from", "date_to",
            "price_quote", "status", "payment_marker",
        )
        read_only_fields = ("id", "status", "payment_marker")

    def validate(self, attrs):
        df, dt = attrs["date_from"], attrs["date_to"]
        if dt <= df:
            raise serializers.ValidationError(_("Дата 'Аренда по' должна быть больше даты 'Аренда с'."))
        return attrs

    def create(self, validated):
        car = Car.objects.select_related("partner").get(pk=validated.pop("car_id"))
        tg_id = validated.pop("client_tg_user_id")

        # не создаём клиента автоматически
        try:
            client = BotUser.objects.get(tg_user_id=tg_id)
        except BotUser.DoesNotExist:
            raise serializers.ValidationError({"detail": "user_not_registered"}, code="user_not_registered")

        if not (client.first_name and client.last_name and client.phone):
            raise serializers.ValidationError({"detail": "user_incomplete"}, code="user_incomplete")

        # телефон из профиля, если не прислали
        if not validated.get("client_phone"):
            validated["client_phone"] = client.phone or ""

        start, end = validated["date_from"], validated["date_to"]

        # проверки занятости
        if qs_overlaps(CarCalendar.objects.filter(car=car), start, end).exists():
            raise serializers.ValidationError(_("Автомобиль занят на выбранные даты."))
        if qs_overlaps(Booking.objects.filter(car=car, status__in=("confirmed", "issued")), start, end).exists():
            raise serializers.ValidationError(_("На эти даты уже есть подтверждённая бронь."))
        fresh = fresh_pending(qs_overlaps(Booking.objects.filter(car=car, status="pending"), start, end),
                              minutes=HOLD_MINUTES)
        if fresh.exists():
            raise serializers.ValidationError(_("Слот временно удерживается другим запросом, попробуйте позже."))

        # если quote не передали — считаем сами
        if validated.get("price_quote") in (None, ""):
            validated["price_quote"] = estimate_quote(car, start, end)

        return Booking.objects.create(car=car, partner=car.partner, client=client, **validated)


class BookingSerializer(serializers.ModelSerializer):
    car_title = serializers.CharField(source="car.title", read_only=True)
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    client_tg_user_id = serializers.IntegerField(source="client.tg_user_id", read_only=True)
    client_selfie_url = serializers.SerializerMethodField()

    # раскрываем для оплат/подсказок
    car_class      = serializers.CharField(source="car.car_class", read_only=True)
    price_weekday  = serializers.DecimalField(source="car.price_weekday", max_digits=12, decimal_places=2, read_only=True)
    price_weekend  = serializers.DecimalField(source="car.price_weekend", max_digits=12, decimal_places=2, read_only=True)
    advance_amount = serializers.DecimalField(source="car.deposit_amount", max_digits=12, decimal_places=2, read_only=True)

    client_first_name = serializers.CharField(source="client.first_name", read_only=True)
    client_last_name  = serializers.CharField(source="client.last_name", read_only=True)
    client_username   = serializers.CharField(source="client.username", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "car", "car_title", "car_class",
            "partner", "partner_name",
            "client", "client_tg_user_id", "client_first_name", "client_last_name", "client_username",
            "client_phone",
            "date_from", "date_to",
            "price_quote",
            "status", "payment_marker",
            "price_weekday", "price_weekend", "advance_amount",
            "created_at", "updated_at", "client_selfie_url"
        )

    def get_client_selfie_url(self, obj):
        selfie = getattr(getattr(obj, "client", None), "selfie_image", None)
        if not selfie:
            return None
        try:
            request = self.context.get("request")
        except Exception:
            request = None
        url = selfie.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


    def to_representation(self, instance):
        data = super().to_representation(instance)
        ctx = self.context or {}
        if ctx.get("redact_client", False) and instance.status not in ("confirmed", "issued", "completed"):
            for key in ("client", "client_tg_user_id", "client_phone",
                        "client_first_name", "client_last_name", "client_username"):
                data[key] = None
        return data


# ---------- ViewSet ----------

class BookingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (BotOnlyPermission,)
    queryset = Booking.objects.select_related("car", "partner", "client")

    def _is_partner_request(self, request):
        qp = request.query_params
        body = getattr(request, "data", {}) or {}
        return bool(qp.get("partner_tg_user_id") or qp.get("partner_username")
                    or body.get("partner_tg_user_id") or body.get("partner_username"))

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", {})
        kwargs["context"].update(self.get_serializer_context())
        if self.action in ("list", "retrieve") and self._is_partner_request(self.request):
            kwargs["context"]["redact_client"] = True
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        return BookingCreateSerializer if self.action == "create" else BookingSerializer

    def _cleanup_expired_confirmed_unpaid(self):
        """
        Лениво отменяем подтверждённые, но не оплаченные брони,
        старше HOLD_MINUTES, и освобождаем CarCalendar.
        """
        now = timezone.now()
        cutoff = now - timezone.timedelta(minutes=HOLD_MINUTES)

        stale = (
            Booking.objects
            .filter(
                status=BookingStatus.CONFIRMED,
                updated_at__lt=cutoff,
            )
            .exclude(payment_marker=PaymentMarker.PAID)
        )

        if not stale.exists():
            return

        for b in stale.select_related("car"):
            CarCalendar.objects.filter(
                car=b.car,
                date_from=b.date_from,
                date_to=b.date_to,
            ).delete()

        stale.update(status=BookingStatus.CANCELED, updated_at=now)

    def get_queryset(self):
        # сначала прибираемся
        self._cleanup_expired_confirmed_unpaid()

        qs = super().get_queryset()
        p_tg = self.request.query_params.get("partner_tg_user_id")
        p_username = self.request.query_params.get("partner_username")
        c_tg = self.request.query_params.get("client_tg_user_id")
        status_q = self.request.query_params.get("status")
        fresh_minutes = int(self.request.query_params.get("fresh_minutes", 0) or 0)

        if p_tg:
            qs = qs.filter(partner__users__tg_user_id=p_tg, partner__users__is_active=True)
        if p_username:
            qs = qs.filter(partner__users__username__iexact=p_username, partner__users__is_active=True)
        if c_tg:
            qs = qs.filter(client__tg_user_id=c_tg)
        if status_q:
            qs = qs.filter(status=status_q)
        if fresh_minutes > 0 and status_q == BookingStatus.PENDING:
            qs = fresh_pending(qs, minutes=fresh_minutes)

        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        booking = ser.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = self.get_queryset().get(pk=pk)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def confirm(self, request, pk=None):
        booking = self.get_queryset().select_for_update().get(pk=pk)
        ser = PartnerActionSerializer(data=request.data); ser.is_valid(raise_exception=True)
        data = ser.validated_data

        q = PartnerUser.objects.filter(partner=booking.partner, is_active=True)
        if data.get("partner_tg_user_id"):
            q = q.filter(tg_user_id=data["partner_tg_user_id"])
        elif data.get("partner_username"):
            q = q.filter(username__iexact=data["partner_username"])
        if not q.exists():
            return Response({"detail": _("Нет прав подтверждать эту бронь.")}, status=403)

        if booking.status != "pending":
            return Response({"detail": _("Бронь не в статусе ожидания.")}, status=400)
        if booking.created_at < timezone.now() - timezone.timedelta(minutes=HOLD_MINUTES):
            booking.status = "expired"; booking.save(update_fields=["status", "updated_at"])
            return Response({"detail": _("Истекло время ожидания подтверждения.")}, status=409)

        start, end = booking.date_from, booking.date_to
        if qs_overlaps(CarCalendar.objects.filter(car=booking.car), start, end).exists():
            return Response({"detail": _("Авто уже занято на эти даты.")}, status=409)
        if qs_overlaps(
            Booking.objects.filter(car=booking.car, status__in=("confirmed", "issued")).exclude(pk=booking.pk),
            start, end
        ).exists():
            return Response({"detail": _("Есть другая подтверждённая бронь в этот период.")}, status=409)

        CarCalendar.objects.create(car=booking.car, date_from=start, date_to=end, status="busy")
        booking.status = "confirmed"
        booking.save(update_fields=["status", "updated_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        booking = self.get_queryset().get(pk=pk)
        ser = PartnerActionSerializer(data=request.data); ser.is_valid(raise_exception=True)
        data = ser.validated_data

        q = PartnerUser.objects.filter(partner=booking.partner, is_active=True)
        if data.get("partner_tg_user_id"):
            q = q.filter(tg_user_id=data["partner_tg_user_id"])
        elif data.get("partner_username"):
            q = q.filter(username__iexact=data["partner_username"])
        if not q.exists():
            return Response({"detail": _("Нет прав отклонять эту бронь.")}, status=403)

        if booking.status != "pending":
            return Response({"detail": _("Бронь уже обработана.")}, status=400)

        booking.status = "rejected"
        booking.save(update_fields=["status", "updated_at"])
        ser = BookingSerializer(booking, context={"redact_client": True})
        return Response(ser.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_queryset().get(pk=pk)
        client_tg_user_id = request.data.get("client_tg_user_id")
        if not client_tg_user_id or booking.client.tg_user_id != int(client_tg_user_id):
            return Response({"detail": _("Можно отменить только собственную бронь.")}, status=403)

        def _free_slot():
            # удаляем блокировку дат, созданную на confirm
            CarCalendar.objects.filter(
                car=booking.car,
                date_from=booking.date_from,
                date_to=booking.date_to,
                status="busy",
            ).delete()

        # pending -> всегда можно отменить (календарь ещё не трогали)
        if booking.status == "pending":
            booking.status = "canceled"
            booking.save(update_fields=["status", "updated_at"])
            return Response(BookingSerializer(booking).data)

        # confirmed & не оплачено & вышел TTL -> отменяем + освобождаем слот
        if booking.status == "confirmed" and (booking.payment_marker or "").lower() != "paid":
            age = timezone.now() - booking.updated_at  # момент confirm-а
            if age.total_seconds() >= HOLD_MINUTES * 60:
                _free_slot()
                booking.status = "canceled"
                booking.save(update_fields=["status", "updated_at"])
                return Response(BookingSerializer(booking).data)

        return Response({"detail": _("Отмена невозможна: бронь уже обработана.")}, status=400)


class PartnerActionSerializer(serializers.Serializer):
    partner_tg_user_id = serializers.IntegerField(required=False)
    partner_username = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get("partner_tg_user_id") and not attrs.get("partner_username"):
            raise serializers.ValidationError(_("Нужно передать partner_tg_user_id или partner_username"))
        return attrs
