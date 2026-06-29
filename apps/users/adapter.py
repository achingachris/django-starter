from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field
from django.utils.translation import gettext_lazy as _


class EmailAsUsernameAdapter(DefaultAccountAdapter):
    """
    Adapter that always sets the username equal to the user's email address.
    """

    def __init__(self, request=None):
        super().__init__(request)
        # Prevent leaking whether someone is already signed up.
        self.error_messages["email_taken"] = _("There was an issue creating the account. Please contact support.")

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
