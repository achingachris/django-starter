import re

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
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


class ProfileEmailUniquenessTest(TestCase):
    """A member must not be able to claim an address that belongs to another account."""

    def setUp(self):
        super().setUp()
        self.attacker = CustomUser.objects.create_user(username="a@example.com", email="a@example.com")
        EmailAddress.objects.create(user=self.attacker, email="a@example.com", verified=True, primary=True)
        self.victim = CustomUser.objects.create_user(username="victim@example.com", email="victim@example.com")
        EmailAddress.objects.create(user=self.victim, email="victim@example.com", verified=False, primary=True)
        self.client.force_login(self.attacker)

    def _post_profile(self, email):
        return self.client.post(reverse("users:user_profile"), {"email": email, "first_name": "", "last_name": ""})

    def test_rejects_another_users_address_in_any_case(self):
        for email in ("victim@example.com", "VICTIM@Example.COM"):
            with self.subTest(email=email):
                response = self._post_profile(email)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "This email address is already in use.")
                self.attacker.refresh_from_db()
                self.assertEqual(self.attacker.email, "a@example.com")

    def test_own_address_is_not_reported_as_in_use(self):
        for email in ("a@example.com", "A@example.com"):
            with self.subTest(email=email):
                response = self._post_profile(email)
                self.assertContains(response, "Profile successfully saved.")
                self.assertNotContains(response, "This email address is already in use.")


class EmailOwnershipWebTest(TestCase):
    """The HTML add-email page and sign-in by code respect one owner per address."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.attacker = CustomUser.objects.create_user(
            username="a@example.com", email="a@example.com", password="attacker-pass-1"
        )
        EmailAddress.objects.create(user=self.attacker, email="a@example.com", verified=True, primary=True)
        # A victim who signed up but has not confirmed their address yet.
        self.victim = CustomUser.objects.create_user(username="victim@example.com", email="victim@example.com")
        EmailAddress.objects.create(user=self.victim, email="victim@example.com", verified=False, primary=True)

    def test_add_email_page_rejects_another_users_address(self):
        self.client.force_login(self.attacker)
        response = self.client.post(reverse("account_email"), {"email": "VICTIM@example.com", "action_add": ""})
        self.assertContains(response, "This email address is already in use.")
        self.assertFalse(EmailAddress.objects.filter(user=self.attacker, email__iexact="victim@example.com").exists())

    def test_login_code_signs_in_the_address_owner(self):
        self.client.force_login(self.attacker)
        self.client.post(
            reverse("users:user_profile"), {"email": "victim@example.com", "first_name": "", "last_name": ""}
        )
        self.client.post(reverse("account_email"), {"email": "victim@example.com", "action_add": ""})
        self.client.logout()

        self.client.post(reverse("account_request_login_code"), {"email": "victim@example.com"})
        self.assertEqual(mail.outbox[-1].to, ["victim@example.com"])
        message = mail.outbox[-1]
        text = message.body + "".join(content for content, _ in getattr(message, "alternatives", []))
        code = re.search(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}\b", text).group(0)
        self.client.post(reverse("account_confirm_login_code"), {"code": code})
        self.assertEqual(self.client.session["_auth_user_id"], str(self.victim.pk))
