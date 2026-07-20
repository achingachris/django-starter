"""
Tests for the service marketplace: role-based dashboards, provider service
CRUD, the client booking flow, the DRF API, and the reminder Celery task.
"""

from datetime import timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.users.models import CustomUser, EmailOTP

from ..models import Booking, Service
from ..tasks import send_booking_reminders

PASSWORD = "Sup3r-Secret-Pass!"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# zero the seconds so the datetime-local round trip (minute precision) is exact
FUTURE = (timezone.now() + timedelta(days=2, hours=1)).replace(second=0, microsecond=0)


def make_user(email, user_type, password=PASSWORD):
    return CustomUser.objects.create_user(username=email, email=email, password=password, user_type=user_type)


class MarketplaceTestBase(TestCase):
    def setUp(self):
        self.client_app = Client()
        self.provider = make_user("pro@example.com", "PROVIDER")
        self.provider.first_name = "Pat"
        self.provider.save()
        self.other_provider = make_user("pro2@example.com", "PROVIDER")
        self.client_user = make_user("cli@example.com", "CLIENT")
        self.service = Service.objects.create(
            provider=self.provider,
            title="House Cleaning",
            description="Deep clean for your home",
            duration_minutes=60,
            price="2500.00",
        )


class HomeRedirectTest(MarketplaceTestBase):
    def test_anonymous_gets_landing(self):
        response = self.client_app.get(reverse("web:home"))
        self.assertEqual(response.status_code, 200)

    def test_client_redirected_to_client_dashboard(self):
        self.client_app.force_login(self.client_user)
        response = self.client_app.get(reverse("web:home"))
        self.assertRedirects(response, reverse("services:client_dashboard"))

    def test_provider_redirected_to_provider_dashboard(self):
        self.client_app.force_login(self.provider)
        response = self.client_app.get(reverse("web:home"))
        self.assertRedirects(response, reverse("services:provider_dashboard"))


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class SignupUserTypeTest(TestCase):
    def _signup(self, user_type):
        return self.client.post(
            reverse("account_signup"),
            {
                "email": f"{user_type.lower()}@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "user_type": user_type,
                "terms_agreement": "on",
            },
        )

    def test_signup_as_provider(self):
        self._signup("PROVIDER")
        otp = EmailOTP.objects.latest("created_at")
        self.client.post(reverse("account_signup_verify"), {"code": otp.code})
        user = CustomUser.objects.get(email="provider@example.com")
        self.assertEqual(user.user_type, "PROVIDER")
        self.assertTrue(user.is_provider)

    def test_signup_defaults_to_client(self):
        self._signup("CLIENT")
        otp = EmailOTP.objects.latest("created_at")
        self.client.post(reverse("account_signup_verify"), {"code": otp.code})
        self.assertEqual(CustomUser.objects.get(email="client@example.com").user_type, "CLIENT")


class ProviderServiceCRUDTest(MarketplaceTestBase):
    def setUp(self):
        super().setUp()
        self.client_app.force_login(self.provider)

    def test_service_list_page(self):
        response = self.client_app.get(reverse("services:service_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "House Cleaning")

    def test_create_modal_get(self):
        response = self.client_app.get(reverse("services:service_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Service")

    def test_create_service(self):
        response = self.client_app.post(
            reverse("services:service_create"),
            {
                "title": "Gardening",
                "description": "Lawn & hedges",
                "duration_minutes": 90,
                "price": "1500.00",
                "active": "on",
            },
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers.get("HX-Refresh"), "true")
        service = Service.objects.get(title="Gardening")
        self.assertEqual(service.provider, self.provider)
        self.assertEqual(service.duration_display, "1h 30min")

    def test_update_service(self):
        response = self.client_app.post(
            reverse("services:service_update", args=[self.service.pk]),
            {"title": "House Cleaning PRO", "description": "x", "duration_minutes": 120, "price": "3000.00"},
        )
        self.assertEqual(response.status_code, 204)
        self.service.refresh_from_db()
        self.assertEqual(self.service.title, "House Cleaning PRO")

    def test_toggle_active(self):
        self.client_app.post(reverse("services:service_toggle_active", args=[self.service.pk]))
        self.service.refresh_from_db()
        self.assertFalse(self.service.active)

    def test_cannot_edit_other_providers_service(self):
        self.client_app.force_login(self.other_provider)
        response = self.client_app.get(reverse("services:service_update", args=[self.service.pk]))
        self.assertEqual(response.status_code, 404)

    def test_delete_blocked_with_upcoming_booking(self):
        Booking.objects.create(client=self.client_user, service=self.service, scheduled_at=FUTURE)
        self.client_app.post(reverse("services:service_delete", args=[self.service.pk]))
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_delete_works_without_live_bookings(self):
        self.client_app.post(reverse("services:service_delete", args=[self.service.pk]))
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())

    def test_client_cannot_access_provider_pages(self):
        self.client_app.force_login(self.client_user)
        response = self.client_app.get(reverse("services:service_list"))
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


class ClientBookingFlowTest(MarketplaceTestBase):
    def setUp(self):
        super().setUp()
        self.client_app.force_login(self.client_user)

    def test_browse_shows_active_services(self):
        other = Service.objects.create(
            provider=self.provider, title="Hidden", duration_minutes=30, price=1, active=False
        )
        response = self.client_app.get(reverse("services:service_browse"))
        self.assertContains(response, "House Cleaning")
        self.assertNotContains(response, other.title)

    def test_browse_search(self):
        Service.objects.create(provider=self.provider, title="Piano Lessons", duration_minutes=45, price="900")
        response = self.client_app.get(reverse("services:service_browse"), {"q": "piano"})
        self.assertContains(response, "Piano Lessons")
        self.assertNotContains(response, "House Cleaning")

    def test_book_service(self):
        response = self.client_app.post(
            reverse("services:service_detail", args=[self.service.pk]),
            {"scheduled_at": FUTURE.strftime("%Y-%m-%dT%H:%M"), "notes": "Gate code 1234"},
        )
        self.assertRedirects(response, reverse("services:my_bookings"))
        booking = Booking.objects.get(client=self.client_user)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.notes, "Gate code 1234")

    def test_booking_in_the_past_rejected(self):
        past = (timezone.now() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
        response = self.client_app.post(
            reverse("services:service_detail", args=[self.service.pk]), {"scheduled_at": past}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)

    def test_overlapping_slot_rejected(self):
        Booking.objects.create(
            client=self.client_user, service=self.service, scheduled_at=FUTURE, status=Booking.Status.CONFIRMED
        )
        response = self.client_app.post(
            reverse("services:service_detail", args=[self.service.pk]),
            {"scheduled_at": (FUTURE + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "overlaps")
        self.assertEqual(Booking.objects.count(), 1)
        # but a slot right after the existing one is fine
        response = self.client_app.post(
            reverse("services:service_detail", args=[self.service.pk]),
            {"scheduled_at": (FUTURE + timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M")},
        )
        self.assertEqual(Booking.objects.count(), 2)

    def test_cancel_own_booking(self):
        booking = Booking.objects.create(client=self.client_user, service=self.service, scheduled_at=FUTURE)
        self.client_app.post(reverse("services:booking_cancel", args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_cannot_cancel_others_booking(self):
        booking = Booking.objects.create(client=self.provider, service=self.service, scheduled_at=FUTURE)
        # client FK allows provider accounts at DB level, but the view scopes to the caller
        other_client = make_user("cli2@example.com", "CLIENT")
        self.client_app.force_login(other_client)
        response = self.client_app.post(reverse("services:booking_cancel", args=[booking.pk]))
        self.assertEqual(response.status_code, 404)


class ProviderBookingManagementTest(MarketplaceTestBase):
    def setUp(self):
        super().setUp()
        self.booking = Booking.objects.create(client=self.client_user, service=self.service, scheduled_at=FUTURE)
        self.client_app.force_login(self.provider)

    def test_dashboard_shows_pending(self):
        response = self.client_app.get(reverse("services:provider_dashboard"))
        self.assertContains(response, "House Cleaning")

    def test_confirm_booking(self):
        response = self.client_app.post(reverse("services:booking_set_status", args=[self.booking.pk, "CONFIRMED"]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(response.status_code, 302)  # non-HTMX posts redirect back

    def test_confirm_then_complete(self):
        self.booking.set_status(Booking.Status.CONFIRMED)
        self.client_app.post(reverse("services:booking_set_status", args=[self.booking.pk, "COMPLETED"]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

    def test_invalid_transition_rejected(self):
        self.booking.set_status(Booking.Status.CANCELLED)
        with self.assertRaises(ValidationError):
            self.booking.set_status(Booking.Status.CONFIRMED)

    def test_htmx_confirm_returns_row_partial(self):
        response = self.client_app.post(
            reverse("services:booking_set_status", args=[self.booking.pk, "CONFIRMED"]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmed")
        self.assertContains(response, f"booking-row-{self.booking.pk}")

    def test_cannot_manage_other_providers_booking(self):
        self.client_app.force_login(self.other_provider)
        response = self.client_app.post(reverse("services:booking_set_status", args=[self.booking.pk, "CONFIRMED"]))
        self.assertEqual(response.status_code, 404)

    def test_provider_cannot_book(self):
        response = self.client_app.get(reverse("services:service_browse"))
        self.assertRedirects(response, reverse("web:home"), fetch_redirect_response=False)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class ReminderTaskTest(MarketplaceTestBase):
    def test_reminders_sent_once_for_confirmed_bookings_in_window(self):
        soon = timezone.now() + timedelta(hours=12)
        booking = Booking.objects.create(
            client=self.client_user, service=self.service, scheduled_at=soon, status=Booking.Status.CONFIRMED
        )
        pending = Booking.objects.create(client=self.client_user, service=self.service, scheduled_at=soon)
        far = Booking.objects.create(
            client=self.client_user,
            service=self.service,
            scheduled_at=timezone.now() + timedelta(days=3),
            status=Booking.Status.CONFIRMED,
        )

        sent = send_booking_reminders()
        booking.refresh_from_db()
        self.assertEqual(sent, 1)
        self.assertIsNotNone(booking.reminder_sent_at)
        # one e-mail each to client and provider
        recipients = {msg.to[0] for msg in mail.outbox}
        self.assertEqual(recipients, {"cli@example.com", "pro@example.com"})

        # second run sends nothing (idempotent)
        self.assertEqual(send_booking_reminders(), 0)
        self.assertIsNone(Booking.objects.get(pk=pending.pk).reminder_sent_at)
        self.assertIsNone(Booking.objects.get(pk=far.pk).reminder_sent_at)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class ApiTest(MarketplaceTestBase):
    def test_services_require_auth(self):
        response = Client().get("/api/services/")
        self.assertEqual(response.status_code, 403)

    def test_service_list_and_mine_scope(self):
        self.client_app.force_login(self.provider)
        response = self.client_app.get("/api/services/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)
        response = self.client_app.get("/api/services/?mine=1")
        self.assertEqual(response.data["results"][0]["provider"]["id"], self.provider.pk)

    def test_provider_can_create_service(self):
        self.client_app.force_login(self.provider)
        response = self.client_app.post(
            "/api/services/",
            {"title": "Tattoo", "duration_minutes": 45, "price": "1200"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Service.objects.get(title="Tattoo").provider, self.provider)

    def test_client_cannot_create_service(self):
        self.client_app.force_login(self.client_user)
        response = self.client_app.post(
            "/api/services/", {"title": "Nope", "duration_minutes": 30, "price": "10"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_booking_api_flow(self):
        # client creates
        self.client_app.force_login(self.client_user)
        response = self.client_app.post(
            "/api/bookings/",
            {"service_id": self.service.pk, "scheduled_at": FUTURE.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        booking_id = response.data["id"]

        # client can't confirm
        response = self.client_app.post(f"/api/bookings/{booking_id}/confirm/")
        self.assertEqual(response.status_code, 403)

        # provider confirms
        self.client_app.force_login(self.provider)
        response = self.client_app.get("/api/bookings/")
        self.assertEqual(response.data["results"][0]["id"], booking_id)
        response = self.client_app.post(f"/api/bookings/{booking_id}/confirm/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "CONFIRMED")

        # provider completes
        response = self.client_app.post(f"/api/bookings/{booking_id}/complete/")
        self.assertEqual(response.data["status"], "COMPLETED")

    def test_api_conflict_returns_400(self):
        Booking.objects.create(
            client=self.client_user, service=self.service, scheduled_at=FUTURE, status=Booking.Status.CONFIRMED
        )
        self.client_app.force_login(self.client_user)
        response = self.client_app.post(
            "/api/bookings/",
            {"service_id": self.service.pk, "scheduled_at": FUTURE.isoformat()},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_schema_includes_marketplace_paths(self):
        self.client_app.force_login(self.provider)
        response = self.client_app.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/api/bookings/", response.content)
        self.assertIn(b"/api/services/", response.content)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class CronEndpointTest(TestCase):
    @override_settings(CRON_SECRET="", DEBUG=True)
    def test_open_in_debug_without_secret(self):
        # no CRON_SECRET configured + DEBUG on -> endpoint is open for local testing
        response = Client().get("/internal/cron/booking-reminders/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("reminders", response.json())

    @override_settings(CRON_SECRET="")
    def test_unconfigured_secret_blocks_production(self):
        # DEBUG is always False under the test runner -> unconfigured cron must not be open
        response = Client().get("/internal/cron/booking-reminders/")
        self.assertEqual(response.status_code, 403)

    @override_settings(CRON_SECRET="topsecret")
    def test_requires_bearer_secret_when_configured(self):
        self.assertEqual(Client().get("/internal/cron/booking-reminders/").status_code, 403)
        response = Client().get("/internal/cron/booking-reminders/", HTTP_AUTHORIZATION="Bearer topsecret")
        self.assertEqual(response.status_code, 200)

    @override_settings(CRON_SECRET="topsecret")
    def test_wrong_secret_rejected(self):
        response = Client().get("/internal/cron/booking-reminders/", HTTP_AUTHORIZATION="Bearer nope")
        self.assertEqual(response.status_code, 403)

    def test_post_not_allowed(self):
        self.assertEqual(Client().post("/internal/cron/booking-reminders/").status_code, 405)
