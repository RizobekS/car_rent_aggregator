# apps/partners/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.choices import PartnerStatus, PartnerUserRole


class Partner(models.Model):
    """Юридическое/физическое лицо-партнёр, владелец автопарка."""
    name = models.CharField(
        _("Название партнёра"),
        max_length=200,
        help_text=_("Отображаемое название компании/ИП")
    )
    phone = models.CharField(
        _("Телефон"),
        max_length=50,
        blank=True
    )
    address = models.CharField(
        _("Адрес"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Адрес партнера")
    )
    email = models.EmailField(
        _("Email"),
        blank=True
    )
    status = models.CharField(
        _("Статус"),
        max_length=20,
        choices=PartnerStatus.choices,
        default=PartnerStatus.PENDING
    )

    # 👇 Новое поле: комиссия агрегатора для этого партнёра, %
    commission_percent = models.DecimalField(
        _("Комиссия агрегатора, %"),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text=_("Сколько % удерживает агрегатор с каждой брони этого партнёра")
    )

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Партнёр")
        verbose_name_plural = _("Партнёры")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class PartnerUser(models.Model):
    """Пользователь от партнёра, который работает через бота/админку."""
    partner = models.ForeignKey(
        Partner,
        verbose_name=_("Партнёр"),
        on_delete=models.CASCADE,
        related_name="users"
    )
    username = models.CharField(
        _("Telegram username"),
        max_length=32,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Без @. Например: webadiko")
    )

    tg_user_id = models.BigIntegerField(_("Telegram user id"), unique=True, db_index=True, blank=True, null=True)

    role = models.CharField(
        _("Роль"),
        max_length=20,
        choices=PartnerUserRole.choices,
        default=PartnerUserRole.MANAGER
    )
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Пользователь партнёра")
        verbose_name_plural = _("Пользователи партнёров")
        indexes = [
            models.Index(fields=["partner", "is_active"]),
        ]

    def __str__(self):
        return f"{self.partner.name} / {self.tg_user_id} ({self.get_role_display()})"


class PartnerAdminLink(models.Model):
    """
    Связка аккаунта Django (админки) с конкретным Partner.
    Пользователи из группы 'Partners' будут видеть в админке только брони своих партнёров.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partner_links",
        verbose_name=_("Админ-пользователь"),
    )
    partner = models.ForeignKey(
        "Partner",
        on_delete=models.CASCADE,
        related_name="admin_links",
        verbose_name=_("Партнёр"),
    )
    is_active = models.BooleanField(_("Активна"), default=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        unique_together = ("user", "partner")
        verbose_name = _("Связь админ-пользователь ↔ партнёр")
        verbose_name_plural = _("Связи админ-пользователь ↔ партнёр")

    def __str__(self) -> str:
        return f"{self.user} ↔ {self.partner} ({'active' if self.is_active else 'inactive'})"
