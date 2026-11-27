from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .helpers import email_in_use_by_another_user, validate_profile_picture
from .models import CustomUser


class CustomUserChangeForm(UserChangeForm):
    email = forms.EmailField(label=_("Email"), required=True)

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name")

    def clean_email(self):
        """Reject an address that already belongs to another account (ACCOUNT_UNIQUE_EMAIL)."""
        email = self.cleaned_data["email"]
        if email_in_use_by_another_user(email, self.instance):
            raise forms.ValidationError(_("This email address is already in use."))
        return email


class UploadAvatarForm(forms.Form):
    avatar = forms.FileField(validators=[validate_profile_picture])


class TermsSignupForm(SignupForm):
    """Signup form that adds a checkbox for accepting the terms.

    The Turnstile captcha comes from ACCOUNT_SIGNUP_FORM_CLASS (apps.users.signup_captcha), which
    allauth uses as the base of every signup form, including the headless API.
    """

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
