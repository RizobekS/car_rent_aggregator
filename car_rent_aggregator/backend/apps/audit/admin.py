# apps/audit/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "actor_kind", "user_badge", "method", "status_code",
        "path_short", "action", "object_model", "object_id", "latency_ms",
    )
    list_filter = (
        "actor_kind", "status_code", "action", "object_model",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = ("path", "view_name", "object_id", "object_model", "actor_label", "ua")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    # ── UI helpers ─────────────────────────────
    def user_badge(self, obj: AuditEvent):
        if obj.user_id:
            badge = "superuser" if obj.is_superuser else ("staff" if obj.is_staff else "user")
            return format_html('<span class="badge badge-info">{}</span> {}', badge, obj.user)
        if obj.actor_kind == "bot":
            return format_html('<span class="badge badge-primary">bot</span> {}', obj.actor_label or "")
        if obj.actor_kind == "webhook":
            return format_html('<span class="badge badge-warning">webhook</span>')
        return format_html('<span class="badge badge-secondary">system</span>')
    user_badge.short_description = _("Кто")

    def path_short(self, obj: AuditEvent):
        p = obj.path or "/"
        return p if len(p) <= 60 else p[:57] + "…"
    path_short.short_description = _("Путь")
