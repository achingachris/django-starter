from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


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
