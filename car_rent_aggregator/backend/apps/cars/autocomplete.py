# apps/museum/autocomplete.py
from dal import autocomplete
from django.db.models import Q
from .models import ModelCar

class ModelCarAutocomplete(autocomplete.Select2QuerySetView):
    """
    Возвращает список Экспозиций (MuseumSection) отфильтрованных по выбранному Блоку.
    DAL сам передаст значение поля 'block' через forward=['block'].
    """
    def get_queryset(self):
        qs = ModelCar.objects.all()

        # фильтр по выбранному блоку (приходит в forwarded)
        mark_id = self.forwarded.get('mark')
        if mark_id:
            qs = qs.filter(mark_id=mark_id)

        # поиск по тексту
        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) |
                Q(name_ru__icontains=self.q) |
                Q(name_uz__icontains=self.q) |
                Q(name_en__icontains=self.q)
            )

        return qs.order_by("name", "id")
