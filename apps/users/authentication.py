from allauth.headless.contrib.rest_framework.authentication import XSessionTokenAuthentication
from django.contrib.auth import HASH_SESSION_KEY
from django.utils.crypto import constant_time_compare
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.exceptions import AuthenticationFailed


class VerifiedXSessionTokenAuthentication(XSessionTokenAuthentication):
    """X-Session-Token authentication that rejects sessions from before a password change.

    allauth's XSessionTokenAuthentication resolves the user from the token's session without the
    session-auth-hash check that django.contrib.auth.get_user applies to cookie sessions, so a token
    issued before a password change or reset kept working on DRF views. This adds that check,
    including SECRET_KEY_FALLBACKS, and flushes stale sessions.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, session = result
        session_hash = session.get(HASH_SESSION_KEY) or ""
        valid_hashes = [user.get_session_auth_hash(), *user.get_session_auth_fallback_hash()]
        if not any(constant_time_compare(session_hash, valid_hash) for valid_hash in valid_hashes):
            session.flush()
            raise AuthenticationFailed("Session expired.")
        return result


class VerifiedXSessionTokenScheme(OpenApiAuthenticationExtension):
    """Describes the X-Session-Token header in the OpenAPI schema (drf-spectacular finds it by target_class)."""

    target_class = "apps.users.authentication.VerifiedXSessionTokenAuthentication"
    name = "XSessionToken"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "header", "name": "X-Session-Token"}
