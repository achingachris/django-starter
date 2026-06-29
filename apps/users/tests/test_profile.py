from allauth.account.models import EmailAddress
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.users.models import CustomUser


class ProfileEmailChangeTest(TestCase):
    """
    Tests for changing the email address on the profile view, and in particular keeping
    allauth's EmailAddress.primary flag in sync with CustomUser.email.
    """

    def setUp(self):
        super().setUp()
        self.user = CustomUser.objects.create(username="old@example.com", email="old@example.com")
        self.user.set_password("password")
        self.user.save()
        # current primary email, plus a second already-verified email the user owns
        EmailAddress.objects.create(user=self.user, email="old@example.com", verified=True, primary=True)
        EmailAddress.objects.create(user=self.user, email="new@example.com", verified=True, primary=False)

        self.client = Client()
        self.client.force_login(self.user)

    def _post_profile(self, email):
        return self.client.post(
            reverse("users:user_profile"),
            {"email": email, "first_name": "", "last_name": "", "language": "en", "timezone": ""},
        )

    def test_change_to_already_verified_email_updates_primary(self):
        response = self._post_profile("new@example.com")
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")

        self.assertEqual(
            EmailAddress.objects.get(user=self.user, primary=True).email,
            "new@example.com",
            "EmailAddress.primary should follow the user's email when changed to an already-verified address",
        )
        self.assertFalse(
            EmailAddress.objects.get(email="old@example.com").primary,
            "the previous address should no longer be primary",
        )

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_change_to_new_address_defers_until_confirmed(self):
        response = self._post_profile("brand-new@example.com")
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.email,
            "old@example.com",
            "email should not change to a brand-new address until it is confirmed",
        )

        new_address = EmailAddress.objects.get(user=self.user, email="brand-new@example.com")
        self.assertFalse(new_address.verified)
        self.assertFalse(new_address.primary)
        self.assertEqual(EmailAddress.objects.get(user=self.user, primary=True).email, "old@example.com")
