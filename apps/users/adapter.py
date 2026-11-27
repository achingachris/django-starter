from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field
from django import forms
from django.utils.translation import gettext_lazy as _

from .helpers import email_in_use_by_another_user


class EmailAsUsernameAdapter(DefaultAccountAdapter):
    """
    Adapter that always sets the username equal to the user's email address.
    """

    def __init__(self, request=None):
        super().__init__(request)
        # Prevent leaking whether someone is already signed up.
        self.error_messages["email_taken"] = _("There was an issue creating the account. Please contact support.")

    def clean_email(self, email):
        """Stop a signed-in user from attaching an address that belongs to another account.

        allauth calls this from its add-email form (the /accounts/email/ page and the headless
        account/email API). With enumeration prevention on, that form would otherwise store another
        account's address as an unverified row on the current user.
        """
        email = super().clean_email(email)
        user = getattr(self.request, "user", None)
        if user is not None and user.is_authenticated and email_in_use_by_another_user(email, user):
            raise forms.ValidationError(_("This email address is already in use."))
        return email

    def populate_username(self, request, user):
        # override the username population to always use the email
        user_field(user, app_settings.USER_MODEL_USERNAME_FIELD, user_email(user))


class NoNewUsersAccountAdapter(DefaultAccountAdapter):
    """
    Adapter that can be used to disable public sign-ups for your app.
    """

    def is_open_for_signup(self, request):
        # see https://stackoverflow.com/a/29799664/8207
        return False
