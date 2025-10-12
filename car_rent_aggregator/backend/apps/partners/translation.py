# apps/partners/translation.py
from modeltranslation.translator import register, TranslationOptions
from django.utils.translation import gettext_lazy as _
from .models import Partner

@register(Partner)
class PartnerTR(TranslationOptions):
    fields = ("name",)
    fallback_values = _('-- sorry, no translation provided --')
