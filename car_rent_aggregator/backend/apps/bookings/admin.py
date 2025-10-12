# apps/bookings/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Booking, BookingExtension

PARTNER_GROUP = "Partners"
REVEAL_STATUSES = ("confirmed", "issued", "completed")  # после этих статусов раскрываем клиента партнёру


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


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Правила:
    - Менеджеры (не в группе Partners): видят все поля и все брони.
    - Партнёры (группа Partners):
        * видят ТОЛЬКО брони тех партнёров, к которым привязаны через PartnerAdminLink;
        * до подтверждения: клиент скрыт;
        * после подтверждения: клиент показан.
    """

    # Состав колонок
    FULL_LIST = (
        "id", "car", "partner",
        "client_public_list",  # читаемое представление клиента для списка
        "date_from", "date_to",
        "price_quote", "status", "payment_marker", "created_at",
    )

    PARTNER_LIST = FULL_LIST  # колонки те же, но содержимое client_public_list зависит от статуса

    readonly_fields = ("created_at", "updated_at")
    list_filter = ("status", "partner")
    search_fields = ("id", "car__title", "partner__name")
    date_hierarchy = "created_at"
    inlines = [BookingExtensionInline]

    # ====== Вспомогательная логика ======
    def _can_reveal_client(self, obj: Booking) -> bool:
        return bool(obj and obj.status in REVEAL_STATUSES)

    def _partner_ids_for_user(self, request):
        """Вернём список partner_id, связанных с этим Django-пользователем через PartnerAdminLink."""
        from apps.partners.models import PartnerAdminLink
        return list(
            PartnerAdminLink.objects.filter(user=request.user, is_active=True)
            .values_list("partner_id", flat=True)
        )

    # ====== Колонки списка ======
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

    # ====== Конфиг формы/списка ======
    def get_list_display(self, request):
        return self.PARTNER_LIST if is_partner_admin(request) else self.FULL_LIST

    def get_fields(self, request, obj=None):
        base = [
            "car", "partner",
            "date_from", "date_to",
            "price_quote", "status", "payment_marker",
            "created_at", "updated_at",
        ]
        if is_partner_admin(request):
            # для партнёра клиентские поля скрыты до подтверждения
            if obj and self._can_reveal_client(obj):
                return ["client", "client_phone"] + base
            return base
        # менеджеры — всегда видят клиента
        return ["client", "client_phone"] + base

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if is_partner_admin(request):
            ro.extend(["client", "client_phone"])
        return ro

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_partner_admin(request):
            partner_ids = self._partner_ids_for_user(request)
            if not partner_ids:
                # нет связей — ничего не показываем
                return qs.none()
            qs = qs.filter(partner_id__in=partner_ids)
        return qs
