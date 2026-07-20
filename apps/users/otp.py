"""
One-time-passcode (OTP) helpers.

An OTP is automatically e-mailed to the user right after they submit one of
the three supported flows:

* ``signup``         - verifying a brand new account during registration
* ``login``          - password-less "email me a sign-in code" flow
* ``password_reset`` - verifying ownership before choosing a new password
"""

import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import EmailOTP

logger = logging.getLogger("apps.users")

OTP_SESSION_KEYS = {
    EmailOTP.Purpose.SIGNUP: "otp_signup",
    EmailOTP.Purpose.LOGIN: "otp_login",
    EmailOTP.Purpose.PASSWORD_RESET: "otp_password_reset",
}

PURPOSE_TITLES = {
    EmailOTP.Purpose.SIGNUP: "Verify your email",
    EmailOTP.Purpose.LOGIN: "Your sign-in code",
    EmailOTP.Purpose.PASSWORD_RESET: "Reset your password",
}

PURPOSE_DESCRIPTIONS = {
    EmailOTP.Purpose.SIGNUP: "Enter the code we e-mailed you to finish creating your account.",
    EmailOTP.Purpose.LOGIN: "Enter the code we e-mailed you to sign in - no password needed.",
    EmailOTP.Purpose.PASSWORD_RESET: "Enter the code we e-mailed you to confirm it's really you.",
}


@dataclass
class VerifyResult:
    success: bool
    message: str
    otp: EmailOTP | None = None


def generate_code() -> str:
    length = settings.OTP_CODE_LENGTH
    return "".join(secrets.choice("0123456789") for _ in range(length))


def send_otp_email(email: str, code: str, purpose: str) -> None:
    """Send the OTP e-mail. Raises on delivery failure so callers can react."""
    title = PURPOSE_TITLES[purpose]
    expiry = settings.OTP_EXPIRY_MINUTES
    subject = f"{title} - {code}"
    text_body = (
        f"{title}\n\n"
        f"Your one-time code is: {code}\n\n"
        f"The code expires in {expiry} minutes. If you did not request it, "
        f"you can safely ignore this e-mail.\n"
    )
    html_body = f"""
    <div style="font-family: Arial, Helvetica, sans-serif; max-width: 480px; margin: 0 auto;
                padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px;">
      <div style="margin-bottom: 20px;">
        <span style="display: inline-block; background: linear-gradient(120deg, #0d7a6f, #0fb5a3);
                     color: #ffffff; font-weight: bold; font-size: 18px; padding: 8px 16px;
                     border-radius: 10px;">Sokoni</span>
      </div>
      <h2 style="margin: 0 0 8px; color: #0d7a6f;">{title}</h2>
      <p style="color: #4b5563; margin: 0 0 24px;">
        Use the one-time code below to continue. It expires in {expiry} minutes.
      </p>
      <div style="text-align: center; margin: 24px 0;">
        <span style="display: inline-block; font-size: 32px; letter-spacing: 8px;
                     font-weight: bold; color: #111827; background: #f3f4f6;
                     padding: 16px 32px; border-radius: 8px;">{code}</span>
      </div>
      <p style="color: #9ca3af; font-size: 13px; margin: 0;">
        If you did not request this code, you can safely ignore this e-mail.
      </p>
    </div>
    """
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    logger.info("Sent %s OTP to %s", purpose, email)


def create_and_send_otp(email: str, purpose: str) -> EmailOTP:
    """
    Invalidate previous codes, create a fresh OTP for (email, purpose) and e-mail it.

    Raises whatever the e-mail backend raises if the message cannot be sent.
    """
    email = email.strip().lower()
    EmailOTP.objects.filter(email__iexact=email, purpose=purpose, is_used=False).update(is_used=True)
    otp = EmailOTP.objects.create(
        email=email,
        code=generate_code(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )
    try:
        send_otp_email(email, otp.code, purpose)
    except Exception:
        # don't leave a dangling code the user will never see
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        raise
    return otp


def resend_cooldown_remaining(email: str, purpose: str) -> int:
    """Seconds the user must still wait before another resend (0 = can resend now)."""
    latest = EmailOTP.latest_active(email, purpose)
    if not latest:
        return 0
    cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
    elapsed = (timezone.now() - latest.created_at).total_seconds()
    return max(0, int(cooldown - elapsed))


def verify_otp(email: str, purpose: str, code: str) -> VerifyResult:
    """
    Check a user-submitted code. On success the OTP is marked used.
    Verification attempts are capped per OTP.
    """
    email = (email or "").strip().lower()
    code = (code or "").strip()
    otp = EmailOTP.latest_active(email, purpose)
    if otp is None:
        return VerifyResult(False, "No active code was found for this e-mail. Please request a new one.")
    if otp.is_expired:
        return VerifyResult(False, "This code has expired. Please request a new one.", otp)
    if otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return VerifyResult(False, "Too many incorrect attempts. Please request a new code.", otp)
    if not secrets.compare_digest(otp.code, code):
        otp.attempts += 1
        if otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            # last allowed attempt used up - invalidate the code entirely
            otp.is_used = True
            otp.save(update_fields=["attempts", "is_used"])
            return VerifyResult(False, "Too many incorrect attempts. Please request a new code.", otp)
        otp.save(update_fields=["attempts"])
        remaining = otp.attempts_remaining
        return VerifyResult(
            False,
            f"Incorrect code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
            otp,
        )
    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return VerifyResult(True, "Code verified.", otp)


def get_pending_email(request, purpose: str) -> str | None:
    data = request.session.get(OTP_SESSION_KEYS[purpose])
    if isinstance(data, dict):
        return data.get("email")
    return None


def set_pending(request, purpose: str, **payload) -> None:
    request.session[OTP_SESSION_KEYS[purpose]] = payload


def clear_pending(request, purpose: str) -> None:
    request.session.pop(OTP_SESSION_KEYS[purpose], None)
