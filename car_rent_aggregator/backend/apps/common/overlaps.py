# apps/common/overlaps.py
from django.db.models import Q
from django.utils import timezone

def qs_overlaps(qs, start, end, field_from="date_from", field_to="date_to"):
    """
    Фильтр пересечений по [start, end). Если end <= start — пусть валидатор модели ловит.
    Условие пересечения: (start < date_to) AND (end > date_from)
    """
    return qs.filter(
        Q(**{f"{field_from}__lt": end}) &
        Q(**{f"{field_to}__gt": start})
    )

def fresh_pending(qs, minutes=20, now=None, field="created_at"):
    """
    Возвращает queryset заявок 'свежих' (TTL hold), созданных за последние N минут.
    Используем при анти-овербукинге.
    """
    now = now or timezone.now()
    cutoff = now - timezone.timedelta(minutes=minutes)
    return qs.filter(**{f"{field}__gte": cutoff})
