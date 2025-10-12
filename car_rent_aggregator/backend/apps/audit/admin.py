# apps/audit/admin.py
from django.contrib import admin
from .models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "actor", "action")
    list_filter  = ("action", "created_at")
    search_fields = ("actor", "action")
    readonly_fields = ("created_at",)
