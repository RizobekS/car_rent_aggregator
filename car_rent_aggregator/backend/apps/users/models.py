# apps/users/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class BotUser(models.Model):
    """Клиент агрегатора в Telegram."""
    tg_user_id = models.BigIntegerField(
        _("Telegram user id"),
        unique=True,
        db_index=True
    )
    username = models.CharField(_("Telegram username"), max_length=32, blank=True, null=True, db_index=True,
                                help_text=_("Без @"))
    selfie_file_id = models.CharField(
        _("Telegram file_id селфи"),
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Сырой file_id фото из Telegram для идентификации клиента")
    )
    selfie_image = models.ImageField(
        _("Селфи"),
        upload_to="selfies/%Y/%m/%d",
        blank=True,
        null=True,
        help_text=_("Файл селфи, сохранённый из Telegram")
    )
    phone = models.CharField(
        _("Телефон"),
        max_length=32,
        blank=True,
        help_text=_("Номер, полученный через request_contact")
    )
    first_name = models.CharField(_("Имя"), max_length=150, blank=True)
    last_name  = models.CharField(_("Фамилия"), max_length=150, blank=True)
    language = models.CharField(
        _("Язык интерфейса"),
        max_length=5,
        default="ru",
        help_text=_("Коды: uz/ru/en")
    )
    is_blocked = models.BooleanField(_("Заблокирован"), default=False)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Пользователь бота")
        verbose_name_plural = _("Пользователи бота")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.tg_user_id} ({self.language})"
