# apps/bookings/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.cars.models import Car
from apps.partners.models import Partner
from apps.users.models import BotUser
from apps.common.choices import BookingStatus, PaymentMarker


class Booking(models.Model):
    """Заявка/бронирование, создаваемая клиентом и подтверждаемая партнёром."""
    car = models.ForeignKey(
        Car,
        verbose_name=_("Автомобиль"),
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    partner = models.ForeignKey(
        Partner,
        verbose_name=_("Партнёр"),
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    client = models.ForeignKey(
        BotUser,
        verbose_name=_("Клиент"),
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    client_phone = models.CharField(_("Телефон клиента"), max_length=32)

    date_from = models.DateTimeField(_("Аренда с"))
    date_to   = models.DateTimeField(_("Аренда по"))

    price_quote = models.DecimalField(
        _("Расчётная стоимость, UZS"),
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        _("Статус брони"),
        max_length=12,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True
    )
    payment_marker = models.CharField(
        _("Оплата брони"),
        max_length=8,
        choices=PaymentMarker.choices,
        default=PaymentMarker.UNPAID
    )

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Бронирование")
        verbose_name_plural = _("Бронирования")
        indexes = [
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["car", "date_from", "date_to"]),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_to <= self.date_from:
            raise ValidationError(_("Дата 'Аренда по' должна быть больше даты 'Аренда с'."))

    def __str__(self):
        return f"#{self.pk} {self.car} {self.date_from:%Y-%m-%d}→{self.date_to:%Y-%m-%d} ({self.get_status_display()})"


class BookingExtension(models.Model):
    """Продление активной брони на N дней после согласования/оплаты."""
    booking = models.ForeignKey(
        Booking,
        verbose_name=_("Бронирование"),
        on_delete=models.CASCADE,
        related_name="extensions"
    )
    prev_end_at = models.DateTimeField(_("Предыдущая дата окончания"))
    new_end_at  = models.DateTimeField(_("Новая дата окончания"))
    days = models.PositiveSmallIntegerField(_("Кол-во добавленных дней"))
    price = models.DecimalField(_("Стоимость продления, UZS"), max_digits=12, decimal_places=2)
    fee   = models.DecimalField(_("Комиссия/сервисный сбор, UZS"), max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(_("Валюта"), max_length=3, default="UZS")
    status = models.CharField(
        _("Статус продления"),
        max_length=10,
        choices=[("pending", _("Ожидает")), ("paid", _("Оплачено")), ("rejected", _("Отклонено"))],
        default="pending"
    )
    payment_order_id = models.CharField(_("Идентификатор оплаты"), max_length=100, blank=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Продление брони")
        verbose_name_plural = _("Продления брони")

    def __str__(self):
        return f"Ext #{self.pk} for booking #{self.booking_id}"
