# apps/cars/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Car

@register(Car)
class CarTR(TranslationOptions):
    fields = ("title",)