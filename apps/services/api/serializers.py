from rest_framework import serializers

from apps.users.models import CustomUser

from ..models import Booking, Service


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("id", "get_display_name", "avatar_url")


class ServiceSerializer(serializers.ModelSerializer):
    provider = ProviderSerializer(read_only=True)
    duration_display = serializers.CharField(read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "provider",
            "title",
            "description",
            "duration_minutes",
            "duration_display",
            "price",
            "active",
            "created_at",
        )
        read_only_fields = ("created_at",)


class BookingSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(active=True), write_only=True, source="service"
    )
    client_email = serializers.EmailField(source="client.email", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "service",
            "service_id",
            "client_email",
            "status",
            "status_display",
            "scheduled_at",
            "notes",
            "created_at",
        )
        read_only_fields = ("status", "created_at")

    def validate_scheduled_at(self, value):
        from django.utils import timezone

        if value < timezone.now():
            raise serializers.ValidationError("Bookings must be in the future.")
        return value

    def validate(self, attrs):
        service = attrs.get("service") or getattr(self.instance, "service", None)
        scheduled_at = attrs.get("scheduled_at") or getattr(self.instance, "scheduled_at", None)
        if (
            service
            and scheduled_at
            and Booking.provider_has_conflict(
                service.provider,
                scheduled_at,
                service.duration_minutes,
                exclude_pk=getattr(self.instance, "pk", None),
            )
        ):
            raise serializers.ValidationError(
                {"scheduled_at": "That slot overlaps another booking. Please choose a different time."}
            )
        return attrs
