"""
E-mail OTP authentication views.

Complete OTP-driven user flow:

* Registration      - submit the signup form and an OTP is automatically
                      e-mailed; the account is only created once it is verified.
* Sign-in code      - password-less login; an OTP is e-mailed on request and
                      the user is signed in after entering it.
* Password reset    - an OTP is sent to the e-mail associated with the account;
                      the password can be changed once it is verified.
* Resend            - a new OTP can be requested for any of the three flows
                      (rate-limited by OTP_RESEND_COOLDOWN_SECONDS).
* Password change   - classic old-password/new-password form for signed-in users.
"""

import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import make_password
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import (
    EmailLoginCodeForm,
    OTPCodeForm,
    PasswordLoginForm,
    PasswordResetOTPForm,
    RegisterForm,
    SetNewPasswordForm,
)
from .models import CustomUser, EmailOTP
from .otp import (
    PURPOSE_DESCRIPTIONS,
    PURPOSE_TITLES,
    clear_pending,
    create_and_send_otp,
    get_pending_email,
    resend_cooldown_remaining,
    set_pending,
    verify_otp,
)

logger = logging.getLogger("apps.users")

BACKEND = "django.contrib.auth.backends.ModelBackend"

_PURPOSE_VERIFY_URLS = {
    EmailOTP.Purpose.SIGNUP: "account_signup_verify",
    EmailOTP.Purpose.LOGIN: "account_login_code_verify",
    EmailOTP.Purpose.PASSWORD_RESET: "account_reset_password_verify",
}


def _safe_next(request):
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return None


def _success_url(request):
    return _safe_next(request) or settings.LOGIN_REDIRECT_URL


def _try_send_otp(request, email, purpose) -> bool:
    """Create + e-mail an OTP; on delivery failure show an error and return False."""
    try:
        create_and_send_otp(email, purpose)
    except Exception:
        logger.exception("Failed to send %s OTP to %s", purpose, email)
        messages.error(
            request,
            _("We couldn't send the verification e-mail. Please check the address and try again."),
        )
        return False
    return True


def _render_otp_page(request, form, purpose, email):
    return render(
        request,
        "otp_account/verify_otp.html",
        {
            "form": form,
            "purpose": purpose,
            "email": email,
            "page_title": PURPOSE_TITLES[purpose],
            "description": PURPOSE_DESCRIPTIONS[purpose],
            "cooldown": resend_cooldown_remaining(email, purpose),
            "expiry_minutes": settings.OTP_EXPIRY_MINUTES,
        },
    )


# ---------------------------------------------------------------------------
# Registration (signup form -> automatic OTP e-mail -> verify -> account created)
# ---------------------------------------------------------------------------


def register(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            if _try_send_otp(request, email, EmailOTP.Purpose.SIGNUP):
                set_pending(
                    request,
                    EmailOTP.Purpose.SIGNUP,
                    email=email,
                    password_hash=make_password(form.cleaned_data["password1"]),
                    user_type=form.cleaned_data["user_type"],
                    next=_safe_next(request) or "",
                )
                messages.success(request, _("We've e-mailed you a verification code."))
                return redirect("account_signup_verify")
    else:
        form = RegisterForm()

    return render(
        request,
        "otp_account/signup.html",
        {"form": form, "page_title": _("Sign Up"), "next": _safe_next(request) or ""},
    )


def register_verify(request):
    email = get_pending_email(request, EmailOTP.Purpose.SIGNUP)
    if not email:
        messages.error(request, _("Please start the sign up process first."))
        return redirect("account_signup")

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            result = verify_otp(email, EmailOTP.Purpose.SIGNUP, form.cleaned_data["code"])
            if result.success:
                pending = request.session.get("otp_signup", {})
                # guard against a race where the account was created in the meantime
                if CustomUser.objects.filter(email__iexact=email).exists():
                    clear_pending(request, EmailOTP.Purpose.SIGNUP)
                    messages.info(request, _("This account already exists. Please sign in."))
                    return redirect("account_login")
                user = CustomUser(username=email, email=email)
                user.password = pending.get("password_hash") or make_password(None)
                if pending.get("user_type") in CustomUser.UserType.values:
                    user.user_type = pending["user_type"]
                user.save()
                EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
                clear_pending(request, EmailOTP.Purpose.SIGNUP)
                auth_login(request, user, backend=BACKEND)
                messages.success(request, _("Your account is ready - welcome!"))
                return redirect(pending.get("next") or settings.LOGIN_REDIRECT_URL)
            else:
                form.add_error("code", result.message)
    else:
        form = OTPCodeForm()

    return _render_otp_page(request, form, EmailOTP.Purpose.SIGNUP, email)


# ---------------------------------------------------------------------------
# Sign in (password) + password-less sign-in code (OTP)
# ---------------------------------------------------------------------------


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_success_url(request))

    if request.method == "POST":
        form = PasswordLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = CustomUser.objects.filter(email__iexact=email).first()
            if user is not None and user.is_active and user.check_password(password):
                auth_login(request, user, backend=BACKEND)
                messages.success(request, _("Successfully signed in."))
                return redirect(_success_url(request))
            form.add_error(None, _("The e-mail address and/or password you specified are not correct."))
    else:
        form = PasswordLoginForm()

    return render(
        request,
        "otp_account/login.html",
        {"form": form, "page_title": _("Sign In"), "next": _safe_next(request) or ""},
    )


def request_login_code(request):
    """Ask for a sign-in code - the OTP is e-mailed to the account's address."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = EmailLoginCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
            if user is not None and _try_send_otp(request, email, EmailOTP.Purpose.LOGIN):
                set_pending(request, EmailOTP.Purpose.LOGIN, email=email, next=_safe_next(request) or "")
                messages.success(request, _("We've e-mailed you a sign-in code."))
                return redirect("account_login_code_verify")
            if user is None:
                # don't reveal whether the account exists
                messages.info(
                    request,
                    _("If an account exists for that e-mail, a sign-in code is on its way."),
                )
                return redirect("account_request_login_code")
    else:
        form = EmailLoginCodeForm(initial={"email": request.GET.get("email", "")})

    return render(
        request,
        "otp_account/login_code.html",
        {"form": form, "page_title": _("Sign-in code")},
    )


def login_code_verify(request):
    email = get_pending_email(request, EmailOTP.Purpose.LOGIN)
    if not email:
        messages.error(request, _("Please request a sign-in code first."))
        return redirect("account_request_login_code")

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            result = verify_otp(email, EmailOTP.Purpose.LOGIN, form.cleaned_data["code"])
            if result.success:
                user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
                pending = request.session.get("otp_login", {})
                clear_pending(request, EmailOTP.Purpose.LOGIN)
                if user is None:
                    messages.error(request, _("No active account found for this e-mail."))
                    return redirect("account_login")
                auth_login(request, user, backend=BACKEND)
                messages.success(request, _("Successfully signed in."))
                return redirect(pending.get("next") or settings.LOGIN_REDIRECT_URL)
            else:
                form.add_error("code", result.message)
    else:
        form = OTPCodeForm()

    return _render_otp_page(request, form, EmailOTP.Purpose.LOGIN, email)


# ---------------------------------------------------------------------------
# Password reset (OTP to the e-mail on file -> verify -> choose new password)
# ---------------------------------------------------------------------------


def password_reset(request):
    if request.user.is_authenticated:
        return redirect("account_change_password")

    if request.method == "POST":
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
            if user is not None and _try_send_otp(request, email, EmailOTP.Purpose.PASSWORD_RESET):
                set_pending(request, EmailOTP.Purpose.PASSWORD_RESET, email=email, verified=False)
                messages.success(
                    request,
                    _("We've sent a reset code to the e-mail associated with your account."),
                )
                return redirect("account_reset_password_verify")
            if user is None:
                # don't reveal whether the account exists
                messages.info(
                    request,
                    _("If an account exists for that e-mail, a reset code is on its way."),
                )
                return redirect("account_reset_password")
    else:
        form = PasswordResetOTPForm()

    return render(
        request,
        "otp_account/password_reset.html",
        {"form": form, "page_title": _("Reset Password")},
    )


def password_reset_verify(request):
    email = get_pending_email(request, EmailOTP.Purpose.PASSWORD_RESET)
    if not email:
        messages.error(request, _("Please request a reset code first."))
        return redirect("account_reset_password")

    if request.session.get("otp_password_reset", {}).get("verified"):
        return redirect("account_reset_password_confirm")

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            result = verify_otp(email, EmailOTP.Purpose.PASSWORD_RESET, form.cleaned_data["code"])
            if result.success:
                # mark this reset session as verified, unlocking the password form
                pending = request.session.get("otp_password_reset", {})
                pending["verified"] = True
                request.session.modified = True
                return redirect("account_reset_password_confirm")
            else:
                form.add_error("code", result.message)
    else:
        form = OTPCodeForm()

    return _render_otp_page(request, form, EmailOTP.Purpose.PASSWORD_RESET, email)


def password_reset_confirm(request):
    email = get_pending_email(request, EmailOTP.Purpose.PASSWORD_RESET)
    pending = request.session.get("otp_password_reset", {})
    if not email or not pending.get("verified"):
        messages.error(request, _("Please verify your reset code first."))
        return redirect("account_reset_password")

    user = CustomUser.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        clear_pending(request, EmailOTP.Purpose.PASSWORD_RESET)
        messages.error(request, _("No active account found for this e-mail."))
        return redirect("account_login")

    if request.method == "POST":
        form = SetNewPasswordForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.save()
            clear_pending(request, EmailOTP.Purpose.PASSWORD_RESET)
            # signing the user in right away: they proved ownership of the e-mail
            auth_login(request, user, backend=BACKEND)
            messages.success(request, _("Your password has been reset. You are now signed in."))
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = SetNewPasswordForm(user=user)

    return render(
        request,
        "otp_account/password_reset_confirm.html",
        {"form": form, "page_title": _("Choose a new password"), "email": email},
    )


# ---------------------------------------------------------------------------
# Resend OTP (works for signup, sign-in code and password reset)
# ---------------------------------------------------------------------------


@require_POST
def resend_otp(request):
    purpose = request.POST.get("purpose", "")
    if purpose not in _PURPOSE_VERIFY_URLS:
        messages.error(request, _("Unknown verification flow."))
        return redirect("account_login")

    email = get_pending_email(request, purpose)
    if not email:
        messages.error(request, _("Your session has expired - please start again."))
        return redirect("account_login")

    remaining = resend_cooldown_remaining(email, purpose)
    if remaining > 0:
        messages.warning(
            request,
            _("Please wait %(seconds)s seconds before requesting a new code.") % {"seconds": remaining},
        )
    elif _try_send_otp(request, email, purpose):
        messages.success(request, _("A new code has been sent to %(email)s.") % {"email": email})

    return redirect(_PURPOSE_VERIFY_URLS[purpose])


# ---------------------------------------------------------------------------
# Password change (signed-in users)
# ---------------------------------------------------------------------------


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep them signed in
            messages.success(request, _("Your password was successfully updated."))
            return redirect("users:user_profile")
    else:
        form = PasswordChangeForm(request.user)
    form.fields["old_password"].widget.attrs.pop("autofocus", None)

    return render(
        request,
        "otp_account/password_change.html",
        {"form": form, "active_tab": "password", "page_title": _("Change Password")},
    )
