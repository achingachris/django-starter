from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, EmailOTP


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Custom Fields",
            {"fields": ("avatar",)},
        ),
    )  # type: ignore


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "created_at", "expires_at", "attempts", "is_used")
    list_filter = ("purpose", "is_used")
    search_fields = ("email",)
    readonly_fields = ("code", "created_at", "expires_at", "attempts", "is_used")
    ordering = ("-created_at",)
