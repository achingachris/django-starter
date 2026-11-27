from django.test import override_settings
from django.urls import reverse

from .base import TestViewBase


class TestBasicViews(TestViewBase):
    def test_landing_page(self):
        self._assert_200(reverse("web:home"))

    def test_signup(self):
        self._assert_200(reverse("account_signup"))

    def test_login(self):
        self._assert_200(reverse("account_login"))

    def test_terms(self):
        self._assert_200(reverse("web:terms"))

    def test_robots(self):
        self._assert_200(reverse("web:robots.txt"))

    @override_settings(UMAMI_WEBSITE_ID="site-id", UMAMI_SCRIPT_URL="")
    def test_analytics_script_needs_an_explicit_script_url(self):
        response = self.client.get(reverse("web:home"))
        self.assertNotContains(response, "data-website-id")
        self.assertNotContains(response, "analytics.")

    @override_settings(UMAMI_WEBSITE_ID="site-id", UMAMI_SCRIPT_URL="https://stats.example.com/script.js")
    def test_analytics_script_loads_from_the_configured_url(self):
        response = self.client.get(reverse("web:home"))
        self.assertContains(response, 'src="https://stats.example.com/script.js" data-website-id="site-id"')

    def _assert_200(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
