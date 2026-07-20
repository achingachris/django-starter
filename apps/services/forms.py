from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Booking, Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ("title", "description", "duration_minutes", "price", "active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_duration_minutes(self):
        duration = self.cleaned_data["duration_minutes"]
        if duration < 15:
            raise forms.ValidationError(_("Sessions must be at least 15 minutes long."))
        return duration


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("scheduled_at", "notes")
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Anything the provider should know?"}),
        }

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        self.fields["scheduled_at"].widget.attrs["min"] = timezone.now().strftime("%Y-%m-%dT%H:%M")

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data["scheduled_at"]
        if scheduled_at < timezone.now():
            raise forms.ValidationError(_("Please pick a time in the future."))
        if self.service is not None and Booking.provider_has_conflict(
            self.service.provider, scheduled_at, self.service.duration_minutes
        ):
            raise forms.ValidationError(_("That slot overlaps another booking. Please choose a different time."))
        return scheduled_at
