# apps/common/permissions.py
from rest_framework.permissions import BasePermission
from django.conf import settings

class BotOnlyPermission(BasePermission):
    """
    Простейшая защита API для ботов:
    - ожидаем заголовок X-Api-Key == settings.BOTS_API_KEY.
    На PROD — вынеси в secrets/ENV, меняй по необходимости.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("X-Api-Key")
        expected = getattr(settings, "BOTS_API_KEY", None)
        return bool(expected and api_key and api_key == expected)
