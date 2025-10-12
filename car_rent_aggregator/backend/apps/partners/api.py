# apps/partners/api.py
from rest_framework import serializers, views, status
from rest_framework.response import Response
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from apps.common.permissions import BotOnlyPermission
from .models import PartnerUser

def normalize_username(u: str) -> str:
    u = (u or "").strip()
    if u.startswith("@"):
        u = u[1:]
    for pref in ("https://t.me/", "http://t.me/", "t.me/"):
        if u.startswith(pref):
            u = u[len(pref):]
    return u

class LinkSerializer(serializers.Serializer):
    username = serializers.CharField()
    tg_user_id = serializers.IntegerField()

class PartnerLinkView(views.APIView):
    permission_classes = (BotOnlyPermission,)

    @transaction.atomic
    def post(self, request):
        ser = LinkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uname = normalize_username(ser.validated_data["username"])
        tg_id = ser.validated_data["tg_user_id"]

        try:
            puser = PartnerUser.objects.select_for_update().get(username__iexact=uname, is_active=True)
        except PartnerUser.DoesNotExist:
            return Response({"detail": _("Партнёрский пользователь с таким username не найден.")}, status=404)

        if puser.tg_user_id and puser.tg_user_id != tg_id:
            return Response({"detail": _("Этот username уже привязан к другому Telegram ID.")}, status=409)

        if puser.tg_user_id != tg_id:
            puser.tg_user_id = tg_id
            puser.save(update_fields=["tg_user_id"])

        return Response({"ok": True, "partner_user_id": puser.id, "partner_id": puser.partner_id}, status=200)
