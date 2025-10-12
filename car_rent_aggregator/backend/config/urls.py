# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.bookings.api import BookingViewSet
from apps.payments.api import PaymentViewSet
from apps.payments.views import PaymentRedirectView
from apps.cars.api import CarsSearchView
from apps.users.api import RegisterView, CheckView
from apps.partners.api import PartnerLinkView
from apps.payments.webhooks import PaymeWebhookView, ClickWebhookView

from .views import ActivateLanguageView

router = DefaultRouter()
router.register(r"bookings", BookingViewSet, basename="bookings")
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
                  path("set_language/<str:lang>/",
                       ActivateLanguageView.as_view(), name="set_language_from_url"),
                  path("admin/", admin.site.urls),
                  path('i18n/', include('django.conf.urls.i18n')),
                  path("api/", include([
                      path("", include(router.urls)),
                      path("cars/search/", CarsSearchView.as_view(), name="cars-search"),
                      path("users/register/", RegisterView.as_view(), name="users-register"),
                      path("users/check/",    CheckView.as_view()),
                      path("partners/link/", PartnerLinkView.as_view(), name="partners-link"),
                      # ⬇️ Вебхуки PayTechUZ — по одному URL без action:
                      path("payments/payme/webhook/", PaymeWebhookView.as_view(), name="payme-webhook"),
                      path("payments/click/webhook/", ClickWebhookView.as_view(), name="click-webhook"),
                      path("payments/p/<str:invoice_id>/", PaymentRedirectView.as_view(), name="payment_redirect"),
                  ])),
              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
              + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
