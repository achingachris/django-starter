from django.contrib import admin

from .models import Booking, Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "duration_minutes", "price", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("title", "provider__email")
    autocomplete_fields = ("provider",)
    ordering = ("-created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("service", "client", "status", "scheduled_at", "created_at")
    list_filter = ("status",)
    search_fields = ("service__title", "client__email", "service__provider__email")
    autocomplete_fields = ("client", "service")
    date_hierarchy = "scheduled_at"
    ordering = ("-scheduled_at",)
