# apps/payments/admin.py
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "invoice_id", "amount", "currency", "status",
                    "booking", "created_at")
    list_filter  = ("provider", "status", "currency")
    search_fields = ("invoice_id", "booking__id")
    readonly_fields = ("created_at", "updated_at")
