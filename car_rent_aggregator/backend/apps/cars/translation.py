# apps/cars/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Car, Region, MarkCar, ModelCar, ColorCar


@register(Car)
class CarTR(TranslationOptions):
    fields = ("title",)

@register(Region)
class RegionTR(TranslationOptions):
    fields = ("name",)


@register(MarkCar)
class MarkCarTR(TranslationOptions):
    fields = ("name",)


@register(ModelCar)
class ModelCarTR(TranslationOptions):
    fields = ("name",)

@register(ColorCar)
class ColorCarTR(TranslationOptions):
    fields = ("name",)