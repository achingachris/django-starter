import importlib
import os
import runpy
import sys
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

BASE_SETTINGS = settings.BASE_DIR / "config" / "settings" / "base.py"
TOGGLES = ("ACCOUNT_EMAIL_VERIFICATION_ENABLED", "ACCOUNT_LOGIN_BY_CODE_ENABLED")


def load_base_settings(**env):
    """Evaluate base.py in isolation with the given environment, without touching the live settings."""
    clean_env = {k: v for k, v in os.environ.items() if k not in TOGGLES}
    with mock.patch.dict(os.environ, {**clean_env, **env}, clear=True), mock.patch("environ.Env.read_env"):
        return runpy.run_path(str(BASE_SETTINGS))


class EmailVerificationToggleTest(SimpleTestCase):
    def test_verification_is_mandatory_by_default(self):
        values = load_base_settings()
        self.assertEqual(values["ACCOUNT_EMAIL_VERIFICATION"], "mandatory")
        self.assertTrue(values["ACCOUNT_LOGIN_BY_CODE_ENABLED"])

    def test_turning_verification_off_also_turns_off_login_by_code(self):
        values = load_base_settings(ACCOUNT_EMAIL_VERIFICATION_ENABLED="False")
        self.assertEqual(values["ACCOUNT_EMAIL_VERIFICATION"], "none")
        self.assertFalse(values["ACCOUNT_LOGIN_BY_CODE_ENABLED"])

    def test_login_by_code_can_be_set_explicitly(self):
        values = load_base_settings(ACCOUNT_EMAIL_VERIFICATION_ENABLED="False", ACCOUNT_LOGIN_BY_CODE_ENABLED="True")
        self.assertTrue(values["ACCOUNT_LOGIN_BY_CODE_ENABLED"])


class ProductionSettingsGuardTest(SimpleTestCase):
    """prod.py refuses to boot with a placeholder or weak SECRET_KEY, or a wildcard ALLOWED_HOSTS."""

    STRONG_KEY = "k" * 60

    def _import_prod(self, **env):
        values = {
            "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
            "ALLOWED_HOSTS": "example.com",
            "SECRET_KEY": self.STRONG_KEY,
            **env,
        }
        with mock.patch.dict(os.environ, values), mock.patch.dict(sys.modules):
            sys.modules.pop("config.settings.prod", None)
            importlib.import_module("config.settings.prod")

    def test_rejects_weak_secret_keys(self):
        for key in ("change-me-to-a-long-random-secret", "django-insecure-" + "x" * 60, "short-key"):
            with self.subTest(key=key), self.assertRaises(ImproperlyConfigured):
                self._import_prod(SECRET_KEY=key)

    def test_rejects_wildcard_allowed_hosts(self):
        with self.assertRaises(ImproperlyConfigured):
            self._import_prod(ALLOWED_HOSTS="example.com,*")
