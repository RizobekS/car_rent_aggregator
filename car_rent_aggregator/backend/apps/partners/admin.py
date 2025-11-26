# apps/partners/admin.py
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Partner, PartnerUser, PartnerAdminLink
from apps.common.choices import PartnerStatus


@admin.register(Partner)
class PartnerAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ("id", "name", "status", "phone", "address", "email", "created_at")
    list_filter  = ("status", "created_at")
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at", "updated_at")
    actions = ["make_active", "make_blocked", "make_pending"]

    @admin.action(description="Отметить как Активен")
    def make_active(self, request, qs):
        qs.update(status=PartnerStatus.ACTIVE)

    @admin.action(description="Отметить как Заблокирован")
    def make_blocked(self, request, qs):
        qs.update(status=PartnerStatus.BLOCKED)

    @admin.action(description="Отметить как Ожидает модерации")
    def make_pending(self, request, qs):
        qs.update(status=PartnerStatus.PENDING)


@admin.register(PartnerUser)
class PartnerUserAdmin(admin.ModelAdmin):
    list_display = ("id", "partner", "tg_user_id", "role", "is_active", "created_at")
    list_filter  = ("partner", "role", "is_active")
    search_fields = ("tg_user_id", "partner__name")
    readonly_fields = ("created_at",)


@admin.register(PartnerAdminLink)
class PartnerAdminLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "partner", "is_active", "created_at")
    list_filter = ("is_active", "partner")
    search_fields = ("user__username", "user__email", "partner__name")
