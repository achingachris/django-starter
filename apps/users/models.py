import hashlib
import uuid
from functools import cached_property

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.users.helpers import validate_profile_picture


def _get_avatar_filename(instance, filename):
    """Use random filename prevent overwriting existing files & to fix caching issues."""
    return f"profile-pictures/{uuid.uuid4()}.{filename.split('.')[-1]}"


class CustomUser(AbstractUser):
    """
    Add additional fields to the user model here.
    """

    class UserType(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        PROVIDER = "PROVIDER", "Provider"

    avatar = models.FileField(upload_to=_get_avatar_filename, blank=True, validators=[validate_profile_picture])
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.CLIENT,
        help_text="Whether the account books services (client) or offers them (provider).",
    )

    def __str__(self):
        return f"{self.get_full_name()} <{self.email or self.username}>"

    @property
    def is_client(self) -> bool:
        return self.user_type == self.UserType.CLIENT

    @property
    def is_provider(self) -> bool:
        return self.user_type == self.UserType.PROVIDER

    def get_display_name(self) -> str:
        if self.get_full_name().strip():
            return self.get_full_name()
        return self.email or self.username

    @property
    def avatar_url(self) -> str:
        if self.avatar:
            return self.avatar.url
        else:
            return f"https://www.gravatar.com/avatar/{self.gravatar_id}?s=128&d=identicon"

    @property
    def gravatar_id(self) -> str:
        # https://en.gravatar.com/site/implement/hash/
        return hashlib.md5(self.email.lower().strip().encode("utf-8")).hexdigest()

    @cached_property
    def has_verified_email(self):
        return EmailAddress.objects.filter(user=self, verified=True).exists()


class EmailOTP(models.Model):
    """
    A one-time-passcode sent to an email address.

    One OTP is issued per (email, purpose) at a time: creating a new one
    invalidates any previous unused codes for the same pair.
    """

    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Account creation"
        LOGIN = "login", "Sign-in code"
        PASSWORD_RESET = "password_reset", "Password reset"

    email = models.EmailField()
    code = models.CharField(max_length=12)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["email", "purpose", "is_used"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP ({self.purpose}) for {self.email} - {'used' if self.is_used else 'active'}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def attempts_remaining(self) -> int:
        return max(0, settings.OTP_MAX_VERIFY_ATTEMPTS - self.attempts)

    @classmethod
    def latest_active(cls, email: str, purpose: str):
        """Return the most recent unused OTP for this email/purpose (or None)."""
        return cls.objects.filter(email__iexact=email, purpose=purpose, is_used=False).order_by("-created_at").first()
