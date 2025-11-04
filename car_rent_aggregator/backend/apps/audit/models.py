# apps/audit/models.py
from __future__ import annotations
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()


class AuditEvent(models.Model):
    """
    Унифицированная запись аудита.
    Пишется как из middleware (request-аудит), так и из сигналов (domain-аудит).
    """
    # когда
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    # кто
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    actor_kind = models.CharField(
        max_length=32,
        default="user",
        help_text="user | bot | webhook | system",
        db_index=True,
    )
    actor_label = models.CharField(
        max_length=128,
        blank=True,
        help_text="Например: X-Api-Key=bot, PaymeWebhook, ClickWebhook",
    )

    # откуда
    ip = models.GenericIPAddressField(null=True, blank=True)
    ua = models.TextField(blank=True, default="", null=True)
    path = models.CharField(max_length=512, db_index=True, null=True)
    method = models.CharField(max_length=8, db_index=True, null=True)
    status_code = models.IntegerField(null=True, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)

    # что делали
    view_name = models.CharField(max_length=256, blank=True, default="", null=True)
    action = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Например: login, logout, create, update, delete, webhook.success, webhook.fail",
        db_index=True,
        null = True
    )

    # над чем
    object_model = models.CharField(max_length=128, blank=True, default="", db_index=True, null=True)
    object_id = models.CharField(max_length=64, blank=True, default="", db_index=True, null=True)
    object_repr = models.CharField(max_length=256, blank=True, default="", null=True)

    # полезные данные
    changes = models.JSONField(encoder=DjangoJSONEncoder, blank=True, null=True)
    extra = models.JSONField(encoder=DjangoJSONEncoder, blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Событие аудита"
        verbose_name_plural = "События аудита"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["actor_kind", "action"]),
            models.Index(fields=["object_model", "object_id"]),
        ]

    def __str__(self) -> str:
        who = self.actor_kind or "user"
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {who}:{self.action} {self.path} → {self.status_code}"
