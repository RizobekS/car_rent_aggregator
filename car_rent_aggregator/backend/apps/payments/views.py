# apps/payments/views.py
from django.http import Http404, HttpResponseRedirect
from django.views import View
from .models import Payment

class PaymentRedirectView(View):
    """
    302 на реальную ссылку провайдера.
    Реальный URL держим в raw_meta['provider_url'].
    """
    def get(self, request, invoice_id: str):
        p = Payment.objects.filter(invoice_id=invoice_id).first()
        if not p:
            raise Http404("Payment not found")
        meta = p.raw_meta or {}
        real_url = (
            meta.get("provider_url")
            or (meta.get("click_create") or {}).get("payment_url")
            or (meta.get("payme_create") or {}).get("payment_url")
            or (meta.get("payme_create") or {}).get("link")
            or p.pay_url  # fallback на старые записи
        )
        if not real_url:
            raise Http404("Payment URL is empty")
        return HttpResponseRedirect(real_url)
