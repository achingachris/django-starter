"""
OTP-based authentication routes.

This module is mounted at ``accounts/`` *before* ``allauth.urls`` in
``config/urls.py``. Because Django resolves first-match-wins, the routes whose
names/paths overlap with allauth (login, signup, password reset/change)
transparently take over from the default allauth pages, while every other
allauth route (social logins, e-mail management, ...) keeps working.
"""

from django.urls import path

from . import otp_views

urlpatterns = [
    # registration with e-mail OTP verification
    path("signup/", otp_views.register, name="account_signup"),
    path("signup/verify/", otp_views.register_verify, name="account_signup_verify"),
    # sign in (password) or via a sign-in code (OTP) e-mailed on request
    path("login/", otp_views.login_view, name="account_login"),
    path("login/code/", otp_views.request_login_code, name="account_request_login_code"),
    path("login/code/verify/", otp_views.login_code_verify, name="account_login_code_verify"),
    # password reset with OTP sent to the account's e-mail
    path("password/reset/", otp_views.password_reset, name="account_reset_password"),
    path("password/reset/verify/", otp_views.password_reset_verify, name="account_reset_password_verify"),
    path("password/reset/confirm/", otp_views.password_reset_confirm, name="account_reset_password_confirm"),
    # resend a code for any of the three flows above
    path("otp/resend/", otp_views.resend_otp, name="account_resend_otp"),
    # password change for signed-in users
    path("password/change/", otp_views.password_change, name="account_change_password"),
]
