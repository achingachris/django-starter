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

    def _assert_200(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
