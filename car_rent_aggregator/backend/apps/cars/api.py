from rest_framework import serializers, generics
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Car, CarCalendar
from apps.bookings.models import Booking
from apps.common.permissions import BotOnlyPermission
from apps.common.overlaps import qs_overlaps

# ---- нормализация значений choices (принимаем код или человекочитаемое имя/синоним) ----

def _choices_map(field):
    code_to_label = {str(code): str(label) for code, label in field.choices}
    label_to_code = {str(label).lower(): str(code) for code, label in field.choices}
    return code_to_label, label_to_code

def normalize_choice(model_cls, field_name: str, raw: str | None) -> str | None:
    if not raw:
        return None
    field = model_cls._meta.get_field(field_name)
    code_to_label, label_to_code = _choices_map(field)
    raws = [str(raw), str(raw).strip(), str(raw).strip().lower()]
    for r in raws:
        for code in code_to_label.keys():
            if r.lower() == code.lower():
                return code
    if raws[-1] in label_to_code:
        return label_to_code[raws[-1]]
    syn = {
        "car_class": {
            "эконом": "eco", "econom": "eco", "economy": "eco", "eco": "eco",
            "комфорт": "comfort", "comfort": "comfort",
            "бизнес": "business", "business": "business",
            "премиум": "premium", "premium": "premium", "lux": "premium", "люкс": "premium",
            "внедорожник": "suv", "suv": "suv", "джип": "suv",
            "минивэн": "minivan", "minivan": "minivan",
        },
        "gearbox": {
            "ат": "AT", "автомат": "AT", "automatic": "AT", "auto": "AT", "at": "AT",
            "мт": "MT", "механика": "MT", "manual": "MT", "mt": "MT",
            "робот": "AMT", "amt": "AMT",
            "вариатор": "CVT", "cvt": "CVT",
        }
    }
    key = "gearbox" if field_name == "gearbox" else "car_class"
    return syn[key].get(raws[-1])

# ---- сериализаторы/вью ----

class CarSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source="partner.name", read_only=True)
    images = serializers.SerializerMethodField()
    images_rel = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    cover_rel = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = (
            "id", "partner", "partner_name", "region",
            "title", "mark", "model", "year",
            "car_class", "gearbox", "plate_number",
            # новые поля
            "mileage_km", "engine_volume_l", "horsepower_hp",
            "fuel_type", "fuel_consumption_l_per_100km",
            "drive_type", "color", "insurance_included", "child_seat",
            "car_with_driver",
            # цены/условия
            "price_weekday", "price_weekend",
            "deposit", "deposit_amount", "limit_km", "delivery",
            "age_access", "drive_exp", "passport",
            # медиа
            "active", "images", "images_rel", "cover_url", "cover_rel",
        )

    def _get_lang(self) -> str:
        ctx = getattr(self, "context", {}) or {}
        return ctx.get("lang") or "ru"

    def get_region(self, obj):
        if not obj.region:
            return None
        lang = self._get_lang()
        field_name = f"name_{lang}"
        val = getattr(obj.region, field_name, None)
        return val or obj.region.name

    def get_color(self, obj):
        if not obj.color:
            return None
        lang = self._get_lang()
        field_name = f"name_{lang}"
        val = getattr(obj.color, field_name, None)
        return val or obj.color.name


    def _file_url(self, f):
        request = self.context.get("request")
        try:
            return request.build_absolute_uri(f.url) if request and f else None
        except Exception:
            return None

    def _file_rel(self, f):
        try:
            return f.name if f else None
        except Exception:
            return None

    def get_images(self, obj):
        im = getattr(obj, "images", None)
        files = im.files() if im else []
        return [u for u in (self._file_url(f) for f in files) if u]

    def get_images_rel(self, obj):
        im = getattr(obj, "images", None)
        files = im.files() if im else []
        return [p for p in (self._file_rel(f) for f in files) if p]

    def get_cover_url(self, obj):
        im = getattr(obj, "images", None)
        return self._file_url(im.image1) if im and im.image1 else None

    def get_cover_rel(self, obj):
        im = getattr(obj, "images", None)
        return self._file_rel(im.image1) if im and im.image1 else None


class CarsSearchParamsSerializer(serializers.Serializer):
    date_from = serializers.DateTimeField(required=False)
    date_to   = serializers.DateTimeField(required=False)
    car_class = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gearbox   = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    max_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)

class CarsSearchView(generics.ListAPIView):
    """
    GET /api/cars/search/?date_from=...&date_to=...&car_class=Эконом&gearbox=Автомат&max_price=300000
    Возвращает доступные автомобили, терпима к локализованным значениям.
    """
    serializer_class = CarSerializer
    permission_classes = (BotOnlyPermission,)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        lang = self.request.query_params.get("lang") or "ru"
        ctx["lang"] = lang
        return ctx

    def get_queryset(self):
        params = CarsSearchParamsSerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        qs = Car.objects.filter(active=True)

        cls = normalize_choice(Car, "car_class", (data.get("car_class") or "").strip() or None)
        gbx = normalize_choice(Car, "gearbox",   (data.get("gearbox")   or "").strip() or None)

        if cls:
            qs = qs.filter(car_class=cls)
        if gbx:
            qs = qs.filter(gearbox=gbx)
        if price := data.get("max_price"):
            qs = qs.filter(Q(price_weekday__lte=price) | Q(price_weekend__lte=price))

        start = data.get("date_from")
        end   = data.get("date_to")
        if start and end:
            busy_car_ids = set(
                qs_overlaps(CarCalendar.objects.filter(status="busy"), start, end)
                .values_list("car_id", flat=True)
            )
            booked_car_ids = set(
                qs_overlaps(Booking.objects.filter(status__in=("confirmed", "issued")), start, end)
                .values_list("car_id", flat=True)
            )
            qs = qs.exclude(id__in=(busy_car_ids | booked_car_ids))
            if self.request.query_params.get("debug") == "1":
                print("[CAR-SEARCH-DEBUG]",
                      "cls=", cls, "gbx=", gbx,
                      "busy=", len(busy_car_ids), "booked=", len(booked_car_ids),
                      "final_count=", qs.exclude(id__in=(busy_car_ids | booked_car_ids)).count())

        return qs.select_related("partner", "images").order_by("partner_id", "mark_id", "model_id", "-year")
