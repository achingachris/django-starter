import logging

import requests
from django import forms
from django.conf import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileFieldsForm(forms.Form):
    """Cloudflare Turnstile captcha for every signup form.

    Used as ACCOUNT_SIGNUP_FORM_CLASS, the base allauth builds each signup form on, so the HTML
    signup page and the headless JSON API both check the captcha. allauth imports this module while
    it builds its own forms, so it must not import allauth forms itself.
    """

    turnstile_token = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_turnstile_token(self):
        if not settings.TURNSTILE_SECRET:
            logger.info("No turnstile secret found, not checking captcha")
            return None

        token = self.cleaned_data.get("turnstile_token")
        if not token:
            raise forms.ValidationError("Missing captcha. Please try again.")

        payload = {"secret": settings.TURNSTILE_SECRET, "response": token}
        try:
            response = requests.post(TURNSTILE_VERIFY_URL, data=payload, timeout=10).json()
        except requests.Timeout:
            raise forms.ValidationError("Captcha verification timed out. Please try again.") from None
        except requests.RequestException, ValueError:
            raise forms.ValidationError("Captcha verification failed. Please try again.") from None
        if not response.get("success"):
            raise forms.ValidationError("Invalid captcha. Please try again.")
        return token

    def signup(self, request, user):
        """No extra fields to save; allauth calls this hook on its signup form base class."""
