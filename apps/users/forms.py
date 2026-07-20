import logging

import requests
from allauth.account.forms import SignupForm
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserChangeForm
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .helpers import validate_profile_picture
from .models import CustomUser


class TurnstileSignupForm(SignupForm):
    """
    Sign up form that includes a turnstile captcha.
    """

    turnstile_token = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_turnstile_token(self):
        if not settings.TURNSTILE_SECRET:
            logging.info("No turnstile secret found, not checking captcha")
            return

        turnstile_token = self.cleaned_data.get("turnstile_token", None)
        if not turnstile_token:
            raise forms.ValidationError("Missing captcha. Please try again.")

        turnstile_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        payload = {
            "secret": settings.TURNSTILE_SECRET,
            "response": turnstile_token,
        }
        try:
            response = requests.post(turnstile_url, data=payload, timeout=10).json()
            if not response["success"]:
                raise forms.ValidationError("Invalid captcha. Please try again.")
        except requests.Timeout:
            raise forms.ValidationError("Captcha verification timed out. Please try again.") from None

        return turnstile_token


class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(label=_("Email"), required=True)

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name")


class UploadAvatarForm(forms.Form):
    avatar = forms.FileField(validators=[validate_profile_picture])


class TermsSignupForm(TurnstileSignupForm):
    """Custom signup form to add a checkbox for accepting the terms."""

    terms_agreement = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # blank out overly-verbose help text
        self.fields["password1"].help_text = ""
        link = '<a class="link" href="{}" target="_blank">{}</a>'.format(
            reverse("web:terms"),
            _("Terms and Conditions"),
        )
        self.fields["terms_agreement"].label = mark_safe(_("I agree to the {terms_link}").format(terms_link=link))


# ---------------------------------------------------------------------------
# OTP e-mail flows: registration, sign-in codes, and password reset
# ---------------------------------------------------------------------------
from django.contrib.auth.password_validation import validate_password  # noqa: E402


class OTPCodeForm(forms.Form):
    """The 6-digit code input shown after an OTP has been e-mailed."""

    code = forms.CharField(
        label=_("Verification code"),
        max_length=12,
        min_length=4,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "••••••",
                "class": "text-center tracking-[0.5em] text-xl font-bold",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError(_("The code only contains digits."))
        return code


class RegisterForm(forms.Form):
    """First step of registration: collect credentials, then verify via OTP e-mail."""

    email = forms.EmailField(label=_("Email"), required=True)
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password (again)"), widget=forms.PasswordInput)
    user_type = forms.ChoiceField(
        label=_("I am signing up as a"),
        choices=(("CLIENT", _("Client - I want to book services")), ("PROVIDER", _("Provider - I offer services"))),
        initial="CLIENT",
        widget=forms.RadioSelect,
    )
    terms_agreement = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = ""
        link = '<a class="link" href="{}" target="_blank">{}</a>'.format(
            reverse("web:terms"),
            _("Terms and Conditions"),
        )
        self.fields["terms_agreement"].label = mark_safe(_("I agree to the {terms_link}").format(terms_link=link))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this e-mail already exists. Please sign in instead."))
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("The two password fields didn't match."))
        return cleaned


class EmailLoginCodeForm(forms.Form):
    """Request a password-less sign-in code by e-mail."""

    email = forms.EmailField(label=_("Email"), required=True)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PasswordResetOTPForm(forms.Form):
    """Request a password-reset code; the OTP goes to the e-mail tied to the account."""

    email = forms.EmailField(label=_("Email"), required=True)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class SetNewPasswordForm(forms.Form):
    """Final password-reset step (after the OTP has been verified)."""

    password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("New password (again)"), widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password, user=self.user)
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("The two password fields didn't match."))
        return cleaned


class PasswordLoginForm(forms.Form):
    """Standard e-mail + password sign-in (an optional sign-in code is also offered)."""

    email = forms.EmailField(label=_("Email"), required=True)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
