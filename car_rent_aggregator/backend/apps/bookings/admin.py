# apps/bookings/admin.py
from datetime import timedelta
from django.utils import timezone
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from .models import Booking, BookingExtension

PARTNER_GROUP = "Partners"
REVEAL_STATUSES = ("confirmed", "issued", "completed", "paid")


def is_partner_admin(request) -> bool:
    return (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
        and request.user.groups.filter(name=PARTNER_GROUP).exists()
    )


class BookingExtensionInline(admin.TabularInline):
    model = BookingExtension
    extra = 0
    readonly_fields = ("created_at",)


def _calc_total_sum(booking: Booking) -> float:
    """
    Пересчитать «теоретическую» стоимость аренды за весь период,
    по нашему правилу будни/выходные.
    Если вдруг нет машины или нет цен — вернём booking.price_quote как fallback.
    """
    car = getattr(booking, "car", None)
    if not car:
        return float(booking.price_quote or 0)

    price_wd = car.price_weekday or 0
    price_we = car.price_weekend or 0

    start = booking.date_from
    end   = booking.date_to
    if not start or not end or end <= start:
        return float(booking.price_quote or 0)

    total = 0
    cur = start
    while cur < end:
        # Сутки считаем по дате cur (локально по часовому поясу Ташкент,
        # в админке просто по weekday()).
        # weekday(): 0=Mon ... 5=Sat 6=Sun
        if cur.weekday() in (5, 6):  # суббота/воскресенье
            total += float(price_we)
        else:
            total += float(price_wd)
        cur += timedelta(days=1)

    return round(total, 2)


def _calc_commission(booking: Booking) -> float:
    """
    Комиссия агрегатора = total_sum * (partner.commission_percent / 100)
    """
    partner = getattr(booking, "partner", None)
    if not partner:
        return 0.0
    pct = float(getattr(partner, "commission_percent", 0) or 0)
    total = _calc_total_sum(booking)
    return round(total * pct / 100.0, 2)


def _calc_partner_net(booking: Booking) -> float:
    """
    Сколько остаётся партнёру после комиссии.
    """
    total = _calc_total_sum(booking)
    fee   = _calc_commission(booking)
    return round(total - fee, 2)


@admin.action(description="Отметить как оплачено (ручная проверка)")
def mark_as_paid(modeladmin, request, queryset):
    """
    Админ-действие для ручной проверки poller'а:
    проставляет payment_marker='paid' и, при желании, status='paid'.
    """
    updated = 0
    for booking in queryset:
        # Если уже помечено как оплачено — пропускаем
        if (booking.payment_marker or "").lower() == "paid":
            continue

        booking.payment_marker = "paid"

        booking.status = "paid"

        booking.updated_at = timezone.now()
        booking.save(update_fields=["payment_marker", "status", "updated_at"])
        updated += 1

    messages.success(request, f"Отмечено как оплачено: {updated} броней.")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Правила:
    - Менеджеры (не в группе Partners): видят все поля и все брони.
    - Партнёры (группа Partners):
        * видят ТОЛЬКО брони тех партнёров, к которым привязаны через PartnerAdminLink;
        * до подтверждения: клиент скрыт;
        * после подтверждения: клиент показан.
        * видят расчёт дохода.
    """

    # Базовые колонки
    BASE_LIST = (
        "id", "car", "partner",
        "client_public_list",
        "date_from", "date_to",
        "status", "payment_marker",
    )

    # Финансы (разные для админа/партнёра)
    ADMIN_FIN_COLS   = ("calc_total_sum", "calc_commission", "calc_partner_net", "created_at")
    PARTNER_FIN_COLS = ("calc_total_sum", "calc_partner_net", "created_at")

    readonly_fields = ("created_at", "updated_at")
    list_filter = ("status", "partner")
    search_fields = ("id", "car__title", "partner__name")
    date_hierarchy = "created_at"
    actions = [mark_as_paid]
    inlines = [BookingExtensionInline]

    # ====== Вспомогательная логика ======
    def _can_reveal_client(self, obj: Booking) -> bool:
        return bool(obj and obj.status in REVEAL_STATUSES)

    def get_list_filter(self, request):
        """
        Для партнёров не показываем фильтр по partner,
        чтобы не светить список всех партнёров.
        Для админов всё как было.
        """
        if is_partner_admin(request):
            # только статус
            return ("status",)
        return super().get_list_filter(request)

    def _partner_ids_for_user(self, request):
        """Вернём список partner_id, связанных с этим Django-пользователем через PartnerAdminLink."""
        from apps.partners.models import PartnerAdminLink
        return list(
            PartnerAdminLink.objects.filter(user=request.user, is_active=True)
            .values_list("partner_id", flat=True)
        )

    # ====== Колонки, выводимые в списке ======
    def client_public_list(self, obj: Booking):
        if self._can_reveal_client(obj):
            parts = []
            fn = getattr(getattr(obj, "client", None), "first_name", "") or ""
            ln = getattr(getattr(obj, "client", None), "last_name", "") or ""
            fio = f"{fn} {ln}".strip()
            if fio:
                parts.append(fio)
            un = getattr(getattr(obj, "client", None), "username", None)
            if un:
                parts.append(f"@{un}")
            if obj.client_phone:
                parts.append(obj.client_phone)
            return " • ".join(parts) if parts else _("(нет данных)")
        return "—"
    client_public_list.short_description = _("Клиент")

    def calc_total_sum(self, obj: Booking):
        return _calc_total_sum(obj)
    calc_total_sum.short_description = _("Сумма аренды (UZS)")

    def calc_commission(self, obj: Booking):
        return _calc_commission(obj)
    calc_commission.short_description = _("Комиссия агрегатора (UZS)")

    def calc_partner_net(self, obj: Booking):
        return _calc_partner_net(obj)
    calc_partner_net.short_description = _("Чистыми партнёру (UZS)")

    # ====== Конфиг списка / форм ======
    def get_list_display(self, request):
        if is_partner_admin(request):
            return self.BASE_LIST + self.PARTNER_FIN_COLS
        return self.BASE_LIST + self.ADMIN_FIN_COLS

    def get_fields(self, request, obj=None):
        """
        Поля в форме карточки.
        Партнёр:
          - до подтверждения не видит клиента,
          - всегда видит свои финансы.
        Админ:
          - всегда видит клиента,
          - видит комиссию.
        """
        finance_block_admin = ["calc_total_sum", "calc_commission", "calc_partner_net"]
        finance_block_partner = ["calc_total_sum", "calc_partner_net"]

        base_fields = [
            "car", "partner",
            "date_from", "date_to",
            "status", "payment_marker",
            "created_at", "updated_at",
        ]

        if is_partner_admin(request):
            if obj and self._can_reveal_client(obj):
                partner_fields = ["client", "client_phone"] + base_fields + finance_block_partner
            else:
                partner_fields = base_fields + finance_block_partner
            return partner_fields

        # админ
        return ["client", "client_phone"] + base_fields + finance_block_admin

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        # финполя всегда read-only
        ro.extend(["calc_total_sum", "calc_partner_net", "calc_commission"])
        if is_partner_admin(request):
            # партнёр не редактирует данные клиента руками
            ro.extend(["client", "client_phone"])
        return ro

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("car", "car__partner", "partner", "client")
        if is_partner_admin(request):
            partner_ids = self._partner_ids_for_user(request)
            if not partner_ids:
                return qs.none()
            qs = qs.filter(partner_id__in=partner_ids)
        return qs
