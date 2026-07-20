from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ..models import Booking, Service
from .serializers import BookingSerializer, ServiceSerializer


class IsProvider(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_provider


class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_client


class ServiceViewSet(viewsets.ModelViewSet):
    """
    Providers manage their own listings; any authenticated user can read
    active marketplace services. ``?mine=1`` scopes the list to the caller.
    """

    serializer_class = ServiceSerializer

    def get_queryset(self):
        queryset = Service.objects.select_related("provider")
        if self.request.query_params.get("mine"):
            return queryset.filter(provider=self.request.user)
        if self.action in ("list", "retrieve"):
            return queryset.filter(active=True)
        return queryset.filter(provider=self.request.user)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsProvider()]

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class BookingViewSet(viewsets.ModelViewSet):
    """
    Clients create and cancel their own bookings (``client`` scope);
    providers see bookings made for their services (``provider`` scope) and
    drive the status via ``confirm`` / ``complete`` / ``provider-cancel``.
    """

    serializer_class = BookingSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = Booking.objects.select_related("service", "service__provider", "client")
        if self.request.user.is_provider:
            return queryset.filter(service__provider=self.request.user)
        return queryset.filter(client=self.request.user)

    def get_permissions(self):
        if self.action in ("create", "cancel"):
            return [IsClient()]
        if self.action in ("confirm", "complete", "provider_cancel"):
            return [IsProvider()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

    def _respond_status(self, booking, request):
        return Response(BookingSerializer(booking, context={"request": request}).data)

    def _set_status(self, request, status):
        booking = self.get_object()
        try:
            booking.set_status(status)
        except Exception as exc:
            detail = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            raise ValidationError({"detail": detail}) from exc
        return self._respond_status(booking, request)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._set_status(request, Booking.Status.CONFIRMED)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._set_status(request, Booking.Status.COMPLETED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not booking.can_cancel:
            raise ValidationError({"detail": "This booking can no longer be cancelled."})
        booking.set_status(Booking.Status.CANCELLED)
        return self._respond_status(booking, request)

    @action(detail=True, methods=["post"], url_path="provider-cancel")
    def provider_cancel(self, request, pk=None):
        return self._set_status(request, Booking.Status.CANCELLED)
