"""
End-to-end tests for the e-mail OTP authentication flows:

* registration with OTP verification (incl. resend)
* password login + password-less sign-in code
* password reset via OTP (incl. resend)
* password change for signed-in users
* profile picture upload
"""

import io
import tempfile
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.users.models import CustomUser, EmailOTP

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD = "Sup3r-Secret-Pass!"


def latest_code(email, purpose):
    return EmailOTP.objects.filter(email=email, purpose=purpose, is_used=False).latest("created_at").code


def png_file(name="avatar.png"):
    # 1x1 transparent PNG
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
        b"\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xc8\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    f = io.BytesIO(data)
    f.name = name
    return f


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class RegistrationOTPTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse("account_signup")
        self.verify_url = reverse("account_signup_verify")

    def _signup(self, email="new.user@example.com"):
        return self.client.post(
            self.signup_url,
            {
                "email": email,
                "password1": PASSWORD,
                "password2": PASSWORD,
                "user_type": "CLIENT",
                "terms_agreement": "on",
            },
        )

    def test_signup_sends_otp_and_verifies(self):
        response = self._signup()
        self.assertRedirects(response, self.verify_url)
        # OTP e-mail was sent automatically on submit
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("new.user@example.com", mail.outbox[0].to)
        # user not created yet
        self.assertFalse(CustomUser.objects.filter(email="new.user@example.com").exists())

        # wrong code -> error + attempt counted
        response = self.client.post(self.verify_url, {"code": "000000"})
        self.assertEqual(response.status_code, 200)
        otp = EmailOTP.objects.get(email="new.user@example.com")
        self.assertEqual(otp.attempts, 1)
        self.assertFalse(CustomUser.objects.filter(email="new.user@example.com").exists())

        # correct code -> account created, e-mail verified, user logged in
        response = self.client.post(self.verify_url, {"code": latest_code("new.user@example.com", "signup")})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = CustomUser.objects.get(email="new.user@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertTrue(EmailAddress.objects.filter(user=user, email=user.email, verified=True, primary=True).exists())
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(user.pk))

    def test_signup_duplicate_email_rejected(self):
        CustomUser.objects.create_user(username="taken@example.com", email="taken@example.com", password="x")
        response = self._signup("taken@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "An account with this e-mail already exists. Please sign in instead."
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_page_requires_pending_session(self):
        response = self.client.get(self.verify_url)
        self.assertRedirects(response, self.signup_url)

    def test_resend_signup_otp_respects_cooldown_then_succeeds(self):
        self._signup()
        resend_url = reverse("account_resend_otp")
        # immediate resend is rate-limited...
        response = self.client.post(resend_url, {"purpose": "signup"})
        self.assertRedirects(response, self.verify_url)
        self.assertEqual(len(mail.outbox), 1, "cooldown should block an instant resend")
        # ...but after the cooldown window another code is e-mailed
        otp = EmailOTP.objects.get(email="new.user@example.com")
        otp.created_at = timezone.now() - timedelta(seconds=120)
        otp.save(update_fields=["created_at"])
        response = self.client.post(resend_url, {"purpose": "signup"})
        self.assertRedirects(response, self.verify_url)
        self.assertEqual(len(mail.outbox), 2)
        # and the fresh code verifies
        response = self.client.post(self.verify_url, {"code": latest_code("new.user@example.com", "signup")})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_expired_code_is_rejected(self):
        self._signup()
        otp = EmailOTP.objects.get(email="new.user@example.com")
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save(update_fields=["expires_at"])
        response = self.client.post(self.verify_url, {"code": otp.code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")
        self.assertFalse(CustomUser.objects.filter(email="new.user@example.com").exists())


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class LoginFlowsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="person@example.com", email="person@example.com", password=PASSWORD
        )

    def test_password_login(self):
        response = self.client.post(reverse("account_login"), {"email": "person@example.com", "password": PASSWORD})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))

    def test_password_login_rejects_bad_credentials(self):
        response = self.client.post(reverse("account_login"), {"email": "person@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not correct")
        self.assertIsNone(self.client.session.get("_auth_user_id"))

    def test_signin_code_flow(self):
        request_url = reverse("account_request_login_code")
        verify_url = reverse("account_login_code_verify")

        # the code is e-mailed automatically on submit
        response = self.client.post(request_url, {"email": "person@example.com"})
        self.assertRedirects(response, verify_url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("person@example.com", mail.outbox[0].to)

        # verify the code -> signed in
        response = self.client.post(verify_url, {"code": latest_code("person@example.com", "login")})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))

    def test_signin_code_for_unknown_email_is_silent(self):
        response = self.client.post(reverse("account_request_login_code"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("account_request_login_code"))
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_login_code(self):
        request_url = reverse("account_request_login_code")
        self.client.post(request_url, {"email": "person@example.com"})
        otp = EmailOTP.objects.get(email="person@example.com")
        otp.created_at = timezone.now() - timedelta(seconds=120)
        otp.save(update_fields=["created_at"])
        response = self.client.post(reverse("account_resend_otp"), {"purpose": "login"})
        self.assertRedirects(response, reverse("account_login_code_verify"))
        self.assertEqual(len(mail.outbox), 2)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class PasswordResetOTPTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="person@example.com", email="person@example.com", password=PASSWORD
        )
        self.reset_url = reverse("account_reset_password")
        self.verify_url = reverse("account_reset_password_verify")
        self.confirm_url = reverse("account_reset_password_confirm")

    def test_full_reset_flow(self):
        # 1) request a code -> e-mailed to the address on the account
        response = self.client.post(self.reset_url, {"email": "person@example.com"})
        self.assertRedirects(response, self.verify_url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("person@example.com", mail.outbox[0].to)

        # 2) confirm page locked until OTP verified
        response = self.client.get(self.confirm_url)
        self.assertRedirects(response, self.reset_url)

        # 3) enter the code -> unlock the password form
        response = self.client.post(self.verify_url, {"code": latest_code("person@example.com", "password_reset")})
        self.assertRedirects(response, self.confirm_url)
        response = self.client.get(self.confirm_url)
        self.assertEqual(response.status_code, 200)

        # 4) choose a new password -> updated + signed in
        response = self.client.post(self.confirm_url, {"password1": "Br4nd-New-Pass!", "password2": "Br4nd-New-Pass!"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Br4nd-New-Pass!"))
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))

        # 5) and the old password no longer works
        self.client.logout()
        response = self.client.post(reverse("account_login"), {"email": "person@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_reset_for_unknown_email_is_silent(self):
        response = self.client.post(self.reset_url, {"email": "nobody@example.com"})
        self.assertRedirects(response, self.reset_url)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_reset_code(self):
        self.client.post(self.reset_url, {"email": "person@example.com"})
        otp = EmailOTP.objects.get(email="person@example.com")
        otp.created_at = timezone.now() - timedelta(seconds=120)
        otp.save(update_fields=["created_at"])
        response = self.client.post(reverse("account_resend_otp"), {"purpose": "password_reset"})
        self.assertRedirects(response, self.verify_url)
        self.assertEqual(len(mail.outbox), 2)

    def test_too_many_wrong_attempts_kills_the_code(self):
        self.client.post(self.reset_url, {"email": "person@example.com"})
        for _ in range(5):
            self.client.post(self.verify_url, {"code": "000000"})
        otp = EmailOTP.objects.get(email="person@example.com")
        self.assertTrue(otp.is_used)
        response = self.client.post(self.verify_url, {"code": otp.code})
        self.assertContains(response, "request a new", status_code=200)


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class PasswordChangeTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="person@example.com", email="person@example.com", password=PASSWORD
        )
        self.change_url = reverse("account_change_password")

    def test_password_change_requires_login(self):
        response = self.client.get(self.change_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    def test_password_change(self):
        self.client.login(username="person@example.com", password=PASSWORD)
        response = self.client.post(
            self.change_url,
            {"old_password": PASSWORD, "new_password1": "An0ther-Good-1!", "new_password2": "An0ther-Good-1!"},
        )
        self.assertRedirects(response, reverse("users:user_profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("An0ther-Good-1!"))
        # session is kept alive after the change
        self.assertEqual(str(self.client.session.get("_auth_user_id")), str(self.user.pk))


@override_settings(EMAIL_BACKEND=EMAIL_BACKEND)
class ProfilePictureTest(TestCase):
    def setUp(self):
        self.tmp_media = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.tmp_media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username="person@example.com", email="person@example.com", password=PASSWORD
        )
        self.client.force_login(self.user)

    def test_profile_page_renders_with_avatar(self):
        response = self.client.get(reverse("users:user_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "profile-upload")

    def test_upload_profile_image(self):
        response = self.client.post(reverse("users:upload_profile_image"), {"avatar": png_file()})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar.name.startswith("profile-pictures/"))

    def test_upload_rejects_non_image(self):
        bad = io.BytesIO(b"not an image")
        bad.name = "evil.txt"
        response = self.client.post(reverse("users:upload_profile_image"), {"avatar": bad})
        self.assertEqual(response.status_code, 400)
