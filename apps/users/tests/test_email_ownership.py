from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.test import TestCase

from apps.users.models import CustomUser


class EmailOwnershipTest(TestCase):
    """An address belongs to one account, so a login code sent to it signs in only its owner."""

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

    def test_headless_add_email_rejects_another_users_address(self):
        login = self.client.post(
            "/_allauth/app/v1/auth/login",
            {"email": "a@example.com", "password": "attacker-pass-1"},
            content_type="application/json",
        )
        token = login.json()["meta"]["session_token"]
        response = self.client.post(
            "/_allauth/app/v1/account/email",
            {"email": "victim@example.com"},
            content_type="application/json",
            headers={"X-Session-Token": token},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmailAddress.objects.filter(user=self.attacker, email__iexact="victim@example.com").exists())
