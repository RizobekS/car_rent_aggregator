# apps/cars/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.partners.models import Partner
from apps.common.choices import CarClass, Gearbox, FuelType, DriveType


class Car(models.Model):
    """Карточка автомобиля в автопарке партнёра."""
    partner = models.ForeignKey(
        Partner,
        verbose_name=_("Партнёр"),
        on_delete=models.CASCADE,
        related_name="cars"
    )
    title = models.CharField(_("Название автомобиля для клиента"), max_length=200,
                             help_text=_("Напр.: Chevrolet Cobalt 2022"))
    make  = models.CharField(_("Марка автомобиля"), max_length=100)
    model = models.CharField(_("Модель автомобиля"), max_length=100)
    year  = models.PositiveSmallIntegerField(_("Год выпуска"))

    car_class = models.CharField(_("Класс авто"), max_length=20, choices=CarClass.choices, db_index=True)
    gearbox   = models.CharField(_("Трансмиссия"), max_length=10, choices=Gearbox.choices)

    # ---- новые поля ТЗ ----
    mileage_km = models.PositiveIntegerField(_("Пробег, км"), default=0)
    engine_volume_l = models.DecimalField(_("Объём двигателя, л"), max_digits=4, decimal_places=1,
                                          null=True, blank=True)
    horsepower_hp   = models.PositiveIntegerField(_("Мощность, л.с."), null=True, blank=True)
    fuel_type       = models.CharField(_("Тип топлива"), max_length=10, choices=FuelType.choices,
                                       null=True, blank=True)
    fuel_consumption_l_per_100km = models.DecimalField(_("Расход, л/100 км"), max_digits=5, decimal_places=2,
                                                       null=True, blank=True)
    drive_type = models.CharField(_("Привод"), max_length=10, choices=DriveType.choices,
                                  null=True, blank=True)
    color      = models.CharField(_("Цвет"), max_length=50, blank=True)
    insurance_included = models.BooleanField(_("Страховка включена"), default=False)
    child_seat = models.BooleanField(_("Детское кресло"), default=False)

    # ---- цены/депозиты/прочее ----
    price_weekday = models.DecimalField(_("Цена в будни, UZS"),    max_digits=12, decimal_places=2)
    price_weekend = models.DecimalField(_("Цена в выходные, UZS"), max_digits=12, decimal_places=2)

    deposit_band = models.CharField(
        _("Диапазон залога"), max_length=10,
        choices=[("none", _("Без залога")), ("low", _("Низкий залог")), ("high", _("Высокий залог"))],
        default="low"
    )
    deposit_amount = models.DecimalField(_("Сумма аванса, UZS"), max_digits=12, decimal_places=2,
                                         null=True, blank=True,
                                         help_text=_("Если фиксированная сумма, иначе оставьте пустым"))
    limit_km = models.PositiveIntegerField(_("Суточный лимит, км"), default=200)
    delivery = models.BooleanField(_("Доставка авто возможна"), default=False)
    car_with_driver = models.BooleanField(_("Автомобиль с водителем"), default=False)

    photo_file_id = models.CharField(_("Telegram file_id обложки"), max_length=200, blank=True)
    active = models.BooleanField(_("Опубликован"), default=True)

    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Автомобиль")
        verbose_name_plural = _("Автомобили")
        ordering = ("partner", "make", "model", "year")
        indexes = [
            models.Index(fields=["partner", "active"]),
            models.Index(fields=["car_class", "gearbox"]),
        ]

    def __str__(self):
        return f"{self.title}"


class CarCalendar(models.Model):
    """Диапазоны занятости автомобиля (для блокировки дат)."""
    car = models.ForeignKey(Car, verbose_name=_("Автомобиль"),
                            on_delete=models.CASCADE, related_name="calendar")
    date_from = models.DateTimeField(_("Занят с"))
    date_to   = models.DateTimeField(_("Занят по"))
    status = models.CharField(_("Статус"), max_length=10,
                              choices=[("busy", _("Занято"))], default="busy", db_index=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Календарь занятости")
        verbose_name_plural = _("Календарь занятости (авто)")
        indexes = [models.Index(fields=["car", "date_from", "date_to"])]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_to <= self.date_from:
            raise ValidationError(_("Дата 'Занят по' должна быть больше даты 'Занят с'."))

    def __str__(self):
        return f"{self.car} [{self.date_from} — {self.date_to}]"


class CarImages(models.Model):
    """Набор до 4-х фото для машины. Фото 1 — обязательно (обложка)."""
    car = models.OneToOneField(Car, on_delete=models.CASCADE, related_name="images", verbose_name=_("Автомобиль"))
    image1 = models.ImageField(_("Фото 1 (обложка)"), upload_to="cars/%Y/%m")
    image2 = models.ImageField(_("Фото 2"), upload_to="cars/%Y/%m", blank=True, null=True)
    image3 = models.ImageField(_("Фото 3"), upload_to="cars/%Y/%m", blank=True, null=True)
    image4 = models.ImageField(_("Фото 4"), upload_to="cars/%Y/%m", blank=True, null=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Фото автомобиля")
        verbose_name_plural = _("Фото автомобиля")

    def __str__(self):
        return f"Фото {self.car}"

    def files(self):
        return [self.image1, self.image2, self.image3, self.image4]
