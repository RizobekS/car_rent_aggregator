# apps/common/choices.py
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

class PartnerStatus(TextChoices):
    ACTIVE   = "active",  _("Активен")
    BLOCKED  = "blocked", _("Заблокирован")
    PENDING  = "pending", _("Ожидает модерации")

class PartnerUserRole(TextChoices):
    OWNER   = "owner",   _("Владелец")
    MANAGER = "manager", _("Менеджер")

class CarClass(TextChoices):
    ECO      = "eco",      _("Эконом")
    COMFORT  = "comfort",  _("Комфорт")
    BUSINESS = "business", _("Бизнес")
    PREMIUM  = "premium",  _("Премиум")
    SUV      = "suv",      _("Внедорожник")
    MINIVAN  = "minivan",  _("Минивэн")

class Gearbox(TextChoices):
    AT  = "AT",  _("Автомат")
    MT  = "MT",  _("Механика")
    AMT = "AMT", _("Робот")
    CVT = "CVT", _("Вариатор")

class FuelType(TextChoices):
    PETROL   = "petrol",   _("Бензин")
    DIESEL   = "diesel",   _("Дизель")
    GAS      = "gas",      _("Газ")
    HYBRID   = "hybrid",   _("Гибрид")
    ELECTRIC = "electric", _("Электро")

class DriveType(TextChoices):
    FWD = "fwd", _("Передний")
    RWD = "rwd", _("Задний")
    AWD = "awd", _("Полный")

class BookingStatus(TextChoices):
    PENDING   = "pending",   _("Ожидает подтверждения")
    CONFIRMED = "confirmed", _("Подтверждена")
    REJECTED  = "rejected",  _("Отклонена")
    EXPIRED   = "expired",   _("Истекло время ожидания")
    CANCELED  = "canceled",  _("Отменено клиентом")
    ISSUED    = "issued",    _("Авто выдано")
    COMPLETED = "completed", _("Завершена")

class PaymentMarker(TextChoices):
    UNPAID = "unpaid", _("Не оплачено")
    PAID   = "paid",   _("Оплачено")

class PaymentStatus(TextChoices):
    NEW      = "new",      _("Создан")
    PENDING  = "pending",  _("Ожидает оплаты")
    PAID     = "paid",     _("Оплачен")
    FAILED   = "failed",   _("Ошибка оплаты")
    REFUNDED = "refunded", _("Возврат")

class PaymentProvider(TextChoices):
    CLICK = "click", _("Click")
    PAYME = "payme", _("Payme")
