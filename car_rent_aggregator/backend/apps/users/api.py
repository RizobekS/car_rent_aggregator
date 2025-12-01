# apps/users/api.py
import base64
from datetime import date, datetime
from uuid import uuid4

from django.core.files.base import ContentFile
from rest_framework import serializers, views, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _
from apps.common.permissions import BotOnlyPermission
from .models import BotUser

class BotUserRegisterSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],  # принимаем и DD.MM.YYYY, и ISO
    )
    drive_exp = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
    )

    class Meta:
        model = BotUser
        fields = (
            "tg_user_id",
            "username",
            "first_name",
            "last_name",
            "phone",
            "language",
            "selfie_file_id",
            "birth_date",
            "drive_exp",
        )
        extra_kwargs = {
            "tg_user_id": {"validators": []},

            "first_name": {"required": True, "allow_blank": False},
            "last_name":  {"required": True, "allow_blank": False},
            "phone":      {"required": True, "allow_blank": False},
        }

    def validate(self, attrs):
        # базовая валидация полной анкеты
        miss = []
        for k in ("first_name", "last_name", "phone"):
            if not attrs.get(k):
                miss.append(k)
        if miss:
            raise serializers.ValidationError(
                {"detail": "incomplete_profile", "missing": miss},
                code="incomplete_profile"
            )

        bdate = attrs.get("birth_date")
        if bdate:
            today = date.today()
            age = today.year - bdate.year - (
                    (today.month, today.day) < (bdate.month, bdate.day)
            )
            if age < 18:
                raise serializers.ValidationError(
                    {"detail": "too_young", "min_age": 18},
                    code="too_young",
                )

        # ➕ проверка стажа
        drive_exp = attrs.get("drive_exp")
        if drive_exp is not None:
            if drive_exp <= 0:
                raise serializers.ValidationError(
                    {"detail": "invalid_drive_exp", "min": 1},
                    code="invalid_drive_exp",
                )

        return attrs

    def create(self, validated_data):
        # upsert по tg_user_id
        obj, _ = BotUser.objects.update_or_create(
            tg_user_id=validated_data["tg_user_id"],
            defaults=validated_data
        )
        return obj

class RegisterView(APIView):
    permission_classes = (BotOnlyPermission,)

    def post(self, request):
        ser = BotUserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(BotUserRegisterSerializer(obj).data, status=status.HTTP_201_CREATED)

class CheckView(APIView):
    permission_classes = (BotOnlyPermission,)

    def get(self, request):
        tg = request.query_params.get("tg_user_id")
        if not tg:
            return Response({"detail": "tg_user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tg = int(tg)
        except ValueError:
            return Response({"detail": "tg_user_id must be int"}, status=status.HTTP_400_BAD_REQUEST)

        user = BotUser.objects.filter(tg_user_id=tg).first()
        is_complete = bool(getattr(user, "first_name", None) and getattr(user, "last_name", None) and getattr(user, "phone", None))
        return Response({
            "exists": bool(user),
            "is_complete": is_complete,
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
            "username": getattr(user, "username", None),
            "phone": getattr(user, "phone", None),
            "language": getattr(user, "language", None),
        })

# apps/users/api.py

class SelfieUpdateSerializer(serializers.Serializer):
    tg_user_id = serializers.IntegerField()
    selfie_file_id = serializers.CharField(max_length=200, required=False, allow_blank=True)
    image_b64 = serializers.CharField(required=True)

class SelfieUpdateView(APIView):
    permission_classes = (BotOnlyPermission,)

    def post(self, request):
        ser = SelfieUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tg = ser.validated_data["tg_user_id"]
        selfie_file_id = ser.validated_data.get("selfie_file_id") or ""
        image_b64 = ser.validated_data["image_b64"]

        # режем префикс "data:image/jpeg;base64,..." если он вдруг есть
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        try:
            raw = base64.b64decode(image_b64)
        except Exception:
            return Response(
                {"detail": "invalid_image_b64"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj, _ = BotUser.objects.get_or_create(tg_user_id=tg)

        # сохраняем file_id "на всякий случай"
        if selfie_file_id:
            obj.selfie_file_id = selfie_file_id

        # сохраняем файл в ImageField
        filename = f"selfie_{tg}_{uuid4().hex}.jpg"
        obj.selfie_image.save(filename, ContentFile(raw), save=True)

        return Response({"ok": True})


class LanguageUpdateSerializer(serializers.Serializer):
    tg_user_id = serializers.IntegerField()
    language = serializers.ChoiceField(choices=[("uz", "uz"), ("ru", "ru"), ("en", "en")])


class LanguageUpdateView(APIView):
    permission_classes = (BotOnlyPermission,)

    def post(self, request):
        ser = LanguageUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        tg = ser.validated_data["tg_user_id"]
        lang = ser.validated_data["language"]

        user, _ = BotUser.objects.get_or_create(tg_user_id=tg)
        user.language = lang
        user.save(update_fields=["language", "updated_at"])

        return Response({"ok": True, "language": user.language}, status=status.HTTP_200_OK)

