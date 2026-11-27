from allauth.account.models import EmailAddress
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.users.models import CustomUser


class SessionTokenRevocationTest(TestCase):
    """App session tokens issued before a password change must stop working on the project API."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username="victim@example.com", email="victim@example.com", password="old-pass-Xq9!"
        )
        EmailAddress.objects.create(user=self.user, email="victim@example.com", verified=True, primary=True)

    def _login(self, password):
        response = self.client.post(
            "/_allauth/app/v1/auth/login",
            {"email": "victim@example.com", "password": password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["meta"]["session_token"]

    def _me(self, token):
        return self.client.get(reverse("api_user_me"), headers={"X-Session-Token": token})

    def test_password_change_revokes_other_tokens(self):
        stale_token = self._login("old-pass-Xq9!")
        current_token = self._login("old-pass-Xq9!")
        self.assertEqual(self._me(stale_token).status_code, 200)

        response = self.client.post(
            "/_allauth/app/v1/account/password/change",
            {"current_password": "old-pass-Xq9!", "new_password": "new-pass-Xq9!"},
            content_type="application/json",
            headers={"X-Session-Token": current_token},
        )
        self.assertEqual(response.status_code, 200)
        # The changing device keeps its session; allauth may rotate it and return a new token.
        current_token = response.json().get("meta", {}).get("session_token", current_token)

        self.assertIn(self._me(stale_token).status_code, (401, 403))
        self.assertEqual(self._me(current_token).status_code, 200)
