"""
Celery tasks for the service marketplace.

``send_booking_reminders`` e-mails clients (and providers) one day before a
confirmed booking. It is registered in ``settings.SCHEDULED_TASKS`` (hourly)
and materialized with ``python manage.py bootstrap_celery_tasks``.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Booking

logger = logging.getLogger("apps.services")

REMINDER_WINDOW = timedelta(hours=24)


@shared_task(bind=True, ignore_result=True)
def send_booking_reminders(self):
    """Send a reminder e-mail for confirmed bookings starting in the next 24 hours."""
    now = timezone.now()
    upcoming = Booking.objects.filter(
        status=Booking.Status.CONFIRMED,
        scheduled_at__gte=now,
        scheduled_at__lte=now + REMINDER_WINDOW,
        reminder_sent_at__isnull=True,
    ).select_related("service", "service__provider", "client")

    sent = 0
    for booking in upcoming:
        when = booking.scheduled_at.strftime("%A, %B %d %Y at %H:%M")
        _send_reminder(booking, booking.client, when)
        _send_reminder(booking, booking.provider, when)
        booking.reminder_sent_at = now
        booking.save(update_fields=["reminder_sent_at"])
        sent += 1

    logger.info("Sent reminders for %s booking(s)", sent)
    return sent


def _send_reminder(booking: Booking, recipient, when: str):
    if not recipient.email:
        return
    is_client = recipient == booking.client
    counterpart = booking.provider.get_display_name() if is_client else booking.client.get_display_name()
    try:
        send_mail(
            subject=f"Reminder: {booking.service.title} tomorrow",
            message=(
                f"Hi {recipient.get_display_name()},\n\n"
                f"This is a reminder that “{booking.service.title}” with {counterpart} "
                f"is scheduled for {when}.\n\n"
                f"See you then!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Failed to send booking reminder to %s", recipient.email)
