# apps/audit/signals.py
from __future__ import annotations
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.bookings.models import Booking
from apps.payments.models import Payment
from .models import AuditEvent


def _model_label(instance) -> str:
    m = instance._meta
    return f"{m.app_label}.{m.model_name}"


@receiver(pre_save, sender=Booking)
def _booking_pre_save(sender, instance: Booking, **kwargs):
    if not instance.pk:
        return
    try:
        prev = Booking.objects.get(pk=instance.pk)
    except Booking.DoesNotExist:
        return

    changes = {}
    # отслеживаем ключевые поля
    for f in ("status", "payment_marker", "date_from", "date_to", "partner_id", "car_id"):
        old = getattr(prev, f)
        new = getattr(instance, f)
        if old != new:
            changes[f] = {"old": old, "new": new}

    if changes:
        AuditEvent.objects.create(
            actor_kind="system",
            actor_label="signal",
            path=f"/admin/bookings/booking/{instance.pk}/change/",
            method="PATCH",
            status_code=200,
            view_name="admin:bookings_booking_change",
            action="booking.changed",
            object_model=_model_label(instance),
            object_id=str(instance.pk),
            object_repr=str(instance),
            changes=changes,
            extra=None,
        )


@receiver(post_save, sender=Booking)
def _booking_post_save(sender, instance: Booking, created: bool, **kwargs):
    if created:
        AuditEvent.objects.create(
            actor_kind="system",
            actor_label="signal",
            path="/api/bookings/",
            method="POST",
            status_code=201,
            view_name="bookings-list",
            action="booking.created",
            object_model=_model_label(instance),
            object_id=str(instance.pk),
            object_repr=str(instance),
            changes={"status": {"old": None, "new": instance.status}},
        )


@receiver(post_save, sender=Payment)
def _payment_post_save(sender, instance: Payment, created: bool, **kwargs):
    changes = {"status": instance.status}
    AuditEvent.objects.create(
        actor_kind="system",
        actor_label="signal",
        path="/api/payments/",
        method="POST" if created else "PATCH",
        status_code=201 if created else 200,
        view_name="payments",
        action="payment.created" if created else "payment.changed",
        object_model=_model_label(instance),
        object_id=str(instance.pk),
        object_repr=str(instance),
        changes=changes,
        extra={
            "provider": instance.provider,
            "amount": float(instance.amount) if instance.amount is not None else None,
            "booking_id": instance.booking_id,
        },
    )
