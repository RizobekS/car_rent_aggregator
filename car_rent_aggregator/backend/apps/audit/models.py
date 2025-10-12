# apps/audit/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditEvent(models.Model):
    """Простой аудит действий для расследования и отладки."""
    actor = models.CharField(_("Актор"), max_length=50, help_text=_("Напр.: client:123, partner:45, system"))
    action = models.CharField(_("Действие"), max_length=50, help_text=_("Напр.: booking.create, payment.paid"))
    payload = models.JSONField(_("Данные"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Событие аудита")
        verbose_name_plural = _("События аудита")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["actor", "action"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor} {self.action}"
