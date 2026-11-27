from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.users.models import CustomUser

SIGNUP_URL = "/_allauth/app/v1/auth/signup"


def turnstile_response(success):
    response = mock.Mock()
    response.json.return_value = {"success": success}
    return response


@override_settings(TURNSTILE_KEY="dummy-turnstile-key", TURNSTILE_SECRET="dummy-turnstile-secret")
class HeadlessSignupCaptchaTest(TestCase):
    """The headless signup API must check the Turnstile captcha, like the HTML signup page."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def _signup(self, **extra):
        payload = {"email": "bot@example.com", "password": "Xq9!dummy-pass-1", **extra}
        return self.client.post(SIGNUP_URL, payload, content_type="application/json")

    @mock.patch("apps.users.signup_captcha.requests.post")
    def test_signup_without_token_is_rejected(self, post):
        response = self._signup()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(email="bot@example.com").exists())
        post.assert_not_called()

    @mock.patch("apps.users.signup_captcha.requests.post", return_value=turnstile_response(False))
    def test_signup_with_invalid_token_is_rejected(self, post):
        response = self._signup(turnstile_token="bad")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.filter(email="bot@example.com").exists())

    @mock.patch("apps.users.signup_captcha.requests.post", return_value=turnstile_response(True))
    def test_signup_with_valid_token_creates_the_account(self, post):
        self._signup(turnstile_token="good")
        self.assertTrue(CustomUser.objects.filter(email="bot@example.com").exists())
        post.assert_called_once()

    @mock.patch("apps.users.signup_captcha.requests.post")
    def test_html_signup_without_token_is_still_rejected(self, post):
        response = self.client.post(
            reverse("account_signup"),
            {"email": "bot@example.com", "password1": "Xq9!dummy-pass-1", "terms_agreement": "on"},
        )
        self.assertContains(response, "Missing captcha")
        self.assertFalse(CustomUser.objects.filter(email="bot@example.com").exists())
