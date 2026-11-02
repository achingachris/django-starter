from django.test import TestCase
from django.urls import reverse

from apps.users.models import CustomUser


class HeadlessAuthApiTest(TestCase):
    def test_config_endpoint(self):
        response = self.client.get("/_allauth/app/v1/config")
        self.assertEqual(response.status_code, 200)

    def test_app_login_issues_session_token_accepted_by_drf(self):
        CustomUser.objects.create_user(username="api@example.com", email="api@example.com", password="s3cret-pass")
        response = self.client.post(
            "/_allauth/app/v1/auth/login",
            {"email": "api@example.com", "password": "s3cret-pass"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["meta"]["session_token"]

        response = self.client.get(reverse("api_user_me"), headers={"X-Session-Token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "api@example.com")


class UserMeApiTest(TestCase):
    def test_requires_authentication(self):
        response = self.client.get(reverse("api_user_me"))
        self.assertIn(response.status_code, (401, 403))

    def test_returns_logged_in_user(self):
        user = CustomUser.objects.create_user(username="me@example.com", email="me@example.com", password="12345")
        self.client.force_login(user)
        response = self.client.get(reverse("api_user_me"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], user.id)
