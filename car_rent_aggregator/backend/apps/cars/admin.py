# apps/cars/admin.py
from dal import autocomplete
from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied

from apps.partners.models import PartnerAdminLink
from .models import (
    Car, CarCalendar, CarImages, Region,
    MarkCar, ModelCar, ColorCar,
)

PARTNER_GROUP = "Partners"  # имя группы для партнёрских админов


# ───────────────────────── helpers ─────────────────────────

def is_partner_admin(request) -> bool:
    return (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
        and request.user.groups.filter(name=PARTNER_GROUP).exists()
    )


def partner_ids_for_user(request):
    return list(
        PartnerAdminLink.objects.filter(user=request.user, is_active=True)
        .values_list("partner_id", flat=True)
    )


# ───────────────────────── простые справочники ─────────────────────────

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(ColorCar)
class ColorCarAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(MarkCar)
class MarkCarAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ModelCar)
class ModelCarAdmin(admin.ModelAdmin):
    list_display = ("id", "mark", "name", "created_at")
    list_filter = ("mark",)
    search_fields = ("name", "mark__name")
    ordering = ("mark__name", "name")
    autocomplete_fields = ("mark",)
    readonly_fields = ("created_at", "updated_at")


# ───────────────────────── Форма для Car с зависимой моделью ─────────────────────────

class CarAdminForm(forms.ModelForm):
    """
    Форма для Car:
      - поле `model` показывает только модели выбранной марки.
      - если марка не выбрана: при редактировании берём из instance,
        при первом открытии формы — список моделей пустой, чтобы не засорять выбор.
    """

    class Meta:
        model = Car
        fields = "__all__"
        widgets = {
            "model": autocomplete.ModelSelect2(
                url="model-car-autocomplete",
                forward=["mark"],
                attrs={"data-placeholder": "---------"}
            ),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            data = self.data or {}
            mark_id = data.get("mark") or (self.instance.mark_id if getattr(self.instance, "pk", None) else None)

            if mark_id:
                self.fields["model"].queryset = (
                    ModelCar.objects
                    .filter(mark_id=mark_id)
                    .order_by("name", "id")
                )
            else:
                # Нет выбранного блока — список секций пуст
                self.fields["model"].queryset = ModelCar.objects.none()

        def clean(self):
            cleaned = super().clean()
            mark = cleaned.get("mark")
            model = cleaned.get("model")
            # 2) Страховка: если пользователь как-то выбрал «чужую» секцию — отклоняем
            if mark and model and model.mark_id != mark.id:
                self.add_error("section", "Модель машины не принадлежит выбранной марке.")
            return cleaned


# ───────────────────────── Car + Images ─────────────────────────

class CarImagesInline(admin.StackedInline):
    model = CarImages
    extra = 0
    max_num = 1
    can_delete = True
    fields = ("image1", "image2", "image3", "image4")
    verbose_name = _("Фотографии")
    verbose_name_plural = _("Фотографии")


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    form = CarAdminForm  # ← используем форму с зависимым полем model

    list_display = (
        "id", "title", "partner", "plate_number", "region",
        "mark", "model", "color",
        "car_class", "gearbox", "drive_type",
        "price_weekday", "price_weekend",
        "active",
    )
    list_filter = (
        "active", "car_class", "gearbox", "drive_type",
        "fuel_type", "region", "partner", "mark", "model", "color",
    )
    search_fields = (
        "id", "title",
        "partner__name",
        "mark__name", "model__name",
        "color__name",
        "plate_number",
    )
    list_select_related = (
        "partner", "region", "mark", "model", "color",
    )
    ordering = ("partner", "mark__name", "model__name")

    # FK-ы через автодополнение
    # ВАЖНО: убираем model из autocomplete, чтобы работала фильтрация по mark
    autocomplete_fields = ("partner", "region", "mark", "color")

    inlines = [CarImagesInline]

    fieldsets = (
        (_("Общее"), {
            "fields": (
                "partner",
                "region",
                "plate_number",
                "title",
                "mark", "model",
                "year",
                "car_class", "gearbox", "drive_type",
                "active",
            )
        }),
        (_("Технические данные"), {
            "fields": (
                "mileage_km", "color",
                "engine_volume_l", "horsepower_hp",
                "fuel_type", "fuel_consumption_l_per_100km",
            )
        }),
        (_("Условия и цены"), {
            "fields": (
                "price_weekday", "price_weekend",
                "deposit", "deposit_amount",
                "limit_km",
                "insurance_included", "child_seat",
                "delivery", "car_with_driver",
                "passport", "age_access", "drive_exp"
            )
        }),
    )

    # ограничение видимости по партнёру
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_partner_admin(request):
            ids = partner_ids_for_user(request)
            return qs.filter(partner_id__in=ids) if ids else qs.none()
        return qs

    # ограничение выбора партнёра в форме
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "partner" and is_partner_admin(request):
            ids = partner_ids_for_user(request)
            kwargs["queryset"] = (
                db_field.related_model.objects.filter(pk__in=ids)
                if ids else db_field.related_model.objects.none()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if is_partner_admin(request) and obj:
            ro.append("partner")
        return ro

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # автоподстановка единственного партнёра при создании
        if is_partner_admin(request) and not obj:
            ids = partner_ids_for_user(request)
            if len(ids) == 1 and "partner" in form.base_fields:
                form.base_fields["partner"].initial = ids[0]
        return form

    def save_model(self, request, obj, form, change):
        if is_partner_admin(request):
            allowed = set(partner_ids_for_user(request))
            if not allowed:
                raise PermissionDenied(_("У вас нет привязанных партнёров. Обратитесь к администратору."))
            if not change:
                # создаём новую машину
                if obj.partner_id not in allowed:
                    if len(allowed) == 1:
                        obj.partner_id = next(iter(allowed))
                    else:
                        raise PermissionDenied(_("Нельзя выбрать этого партнёра."))
            else:
                # редактируем существующую машину
                if "partner" in form.changed_data and obj.partner_id not in allowed:
                    raise PermissionDenied(_("Нельзя менять владельца автомобиля."))
        super().save_model(request, obj, form, change)


# ───────────────────────── Календарь авто ─────────────────────────

@admin.register(CarCalendar)
class CarCalendarAdmin(admin.ModelAdmin):
    """
    Календарь доступности/занятости:
    - Партнёры видят только записи по своим машинам.
    - В формах выбирают только «свои» авто.
    - Дополнительно защищаем прямой доступ.
    """
    list_display = ("id", "car", "car_partner", "date_from", "date_to", "status")
    list_filter = ("status", "car__partner")
    search_fields = ("car__title", "car__partner__name")
    list_select_related = ("car", "car__partner")

    def car_partner(self, obj):
        return getattr(obj.car.partner, "name", "-")
    car_partner.short_description = _("Партнёр")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_partner_admin(request):
            ids = partner_ids_for_user(request)
            return qs.filter(car__partner_id__in=ids) if ids else qs.none()
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "car" and is_partner_admin(request):
            ids = partner_ids_for_user(request)
            kwargs["queryset"] = Car.objects.filter(partner_id__in=ids) if ids else Car.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_view_permission(self, request, obj=None):
        base = super().has_view_permission(request, obj)
        if not base:
            return False
        if is_partner_admin(request) and obj is not None:
            return obj.car.partner_id in set(partner_ids_for_user(request))
        return True

    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj)
        if not base:
            return False
        if is_partner_admin(request) and obj is not None:
            return obj.car.partner_id in set(partner_ids_for_user(request))
        return True

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj)
        if not base:
            return False
        if is_partner_admin(request) and obj is not None:
            return obj.car.partner_id in set(partner_ids_for_user(request))
        return True


# ───────────────────────── Фото ─────────────────────────

@admin.register(CarImages)
class CarImagesAdmin(admin.ModelAdmin):
    list_display = ("id", "car", "created_at")
    search_fields = ("car__title", "car__partner__name")
    list_select_related = ("car",)
