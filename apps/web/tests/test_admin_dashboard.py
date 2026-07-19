from django.test import TestCase
from django.urls import reverse

from apps.users.models import CustomUser, UserRole


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.member = CustomUser.objects.create_user(
            username="member@example.com", email="member@example.com", password="testpass123", role=UserRole.MEMBER
        )
        self.admin = CustomUser.objects.create_user(
            username="admin@example.com", email="admin@example.com", password="testpass123", role=UserRole.ADMIN
        )

    def test_member_cannot_access_admin_dashboard(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("web:admin_dashboard"), follow=True)
        self.assertRedirects(response, reverse("web:home"))

    def test_admin_role_can_access_admin_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("web:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse("web:admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    def test_default_role_is_member(self):
        user = CustomUser.objects.create_user(username="new@example.com", email="new@example.com", password="x")
        self.assertEqual(user.role, UserRole.MEMBER)
        self.assertFalse(user.is_admin_role)
