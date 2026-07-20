from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Service(models.Model):
    """A bookable service offered by a provider."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="services",
        limit_choices_to={"user_type": "PROVIDER"},
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60, validators=[MinValueValidator(15)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.provider.get_display_name()})"

    @property
    def duration_display(self) -> str:
        hours, minutes = divmod(self.duration_minutes, 60)
        if hours and minutes:
            return f"{hours}h {minutes}min"
        if hours:
            return f"{hours}h"
        return f"{minutes} min"


class Booking(models.Model):
    """An appointment a client makes for a provider's service."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        limit_choices_to={"user_type": "CLIENT"},
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.service.title} for {self.client.get_display_name()} @ {self.scheduled_at:%Y-%m-%d %H:%M}"

    @property
    def provider(self):
        return self.service.provider

    @property
    def ends_at(self):
        from datetime import timedelta

        return self.scheduled_at + timedelta(minutes=self.service.duration_minutes)

    @property
    def is_upcoming(self) -> bool:
        return self.scheduled_at >= timezone.now() and self.status in (
            self.Status.PENDING,
            self.Status.CONFIRMED,
        )

    @property
    def can_cancel(self) -> bool:
        return self.is_upcoming

    # allowed status transitions, enforced by set_status()
    TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.CANCELLED, Status.COMPLETED},
        Status.CONFIRMED: {Status.COMPLETED, Status.CANCELLED},
        Status.COMPLETED: set(),
        Status.CANCELLED: set(),
    }

    def set_status(self, new_status: str):
        if new_status not in self.TRANSITIONS.get(self.status, set()):
            raise ValidationError(
                _("Cannot move a booking from %(old)s to %(new)s.")
                % {"old": self.get_status_display(), "new": new_status}
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def clean(self):
        super().clean()
        if self.scheduled_at and self.scheduled_at < timezone.now():
            raise ValidationError({"scheduled_at": _("Bookings must be in the future.")})

    @classmethod
    def provider_has_conflict(cls, provider, scheduled_at, duration_minutes, exclude_pk=None) -> bool:
        """True if the provider already has a live booking overlapping the requested slot."""
        from datetime import timedelta

        end = scheduled_at + timedelta(minutes=duration_minutes)
        conflicts = cls.objects.filter(
            service__provider=provider,
            status__in=[cls.Status.PENDING, cls.Status.CONFIRMED],
            scheduled_at__lt=end,
            scheduled_at__gte=scheduled_at - timedelta(days=1),  # bound the overlap scan
        )
        if exclude_pk:
            conflicts = conflicts.exclude(pk=exclude_pk)
        return any(booking.ends_at > scheduled_at for booking in conflicts.select_related("service"))
