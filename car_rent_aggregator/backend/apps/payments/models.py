# apps/payments/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.bookings.models import Booking
from apps.common.choices import PaymentProvider, PaymentStatus


class Payment(models.Model):
    """Платёж за бронь/продление, создаётся до оплаты, подтверждается коллбеком провайдера."""
    booking = models.OneToOneField(
        Booking,
        verbose_name=_("Бронирование"),
        on_delete=models.CASCADE,
        related_name="payment",
        null=True,
        blank=True
    )
    provider = models.CharField(
        _("Провайдер"),
        max_length=10,
        choices=PaymentProvider.choices
    )
    amount = models.DecimalField(_("Сумма, UZS"), max_digits=12, decimal_places=2)
    currency = models.CharField(_("Валюта"), max_length=3, default="UZS")

    invoice_id = models.CharField(_("ID счёта/заказа"), max_length=100, unique=True, db_index=True)
    pay_url    = models.URLField(_("Ссылка на оплату"), max_length=1024, blank=True)

    status = models.CharField(
        _("Статус оплаты"),
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NEW,
        db_index=True
    )
    raw_meta = models.JSONField(_("Сырой ответ провайдера"), default=dict, blank=True)

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Платёж")
        verbose_name_plural = _("Платежи")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_provider_display()} / {self.invoice_id} [{self.get_status_display()}]"
