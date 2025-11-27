# apps/users/admin.py
from django.contrib import admin
from .models import BotUser

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "id", "tg_user_id", "phone", "birth_date", "drive_exp", "language", "is_blocked", "created_at")
    list_filter  = ("language", "is_blocked", "created_at")
    search_fields = ("tg_user_id", "phone", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at", "selfie_file_id")
