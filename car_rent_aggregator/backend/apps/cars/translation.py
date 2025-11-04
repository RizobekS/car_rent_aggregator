# apps/cars/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Car, Region

@register(Car)
class CarTR(TranslationOptions):
    fields = ("title",)

@register(Region)
class RegionTR(TranslationOptions):
    fields = ("name",)