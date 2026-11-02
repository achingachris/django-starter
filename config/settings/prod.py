# flake8: noqa: F405
"""Production settings: imports everything from base.py, then applies prod overrides."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa F401

# Note: it is recommended to use the "DEBUG" environment variable to override this value in base.py.
# A future release may remove it from here.
DEBUG = False

# Unlike base.py, no fallback defaults here: production must never boot on the committed dev
# SECRET_KEY, and "*" is not a safe ALLOWED_HOSTS value. django-environ raises
# ImproperlyConfigured at startup when a variable without a default is missing.
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Production requires a PostgreSQL database via DATABASE_URL. There is no SQLite
# fallback here: fail loudly at startup if it is missing or points elsewhere.
if "DATABASE_URL" not in env:
    raise ImproperlyConfigured("DATABASE_URL must be set in production.")

DATABASES = {"default": env.db("DATABASE_URL")}

if "postgresql" not in str(DATABASES["default"].get("ENGINE", "")):
    raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL.")

# Keep database connections open for reuse between requests instead of reconnecting each time.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# Serve static files directly from the app via WhiteNoise (no separate web server / CDN required).
# Insert the middleware immediately after SecurityMiddleware, per WhiteNoise's docs.
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
# Compress static files at collectstatic time. We avoid the *Manifest* variant because assets
# referenced inside built CSS (fonts/images) can break under hashed-manifest storage.
STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedStaticFilesStorage"

# fix ssl mixed content issues
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Django security checklist settings.
# More details here: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# The __Secure- prefix makes browsers refuse to store these cookies unless they arrive over
# HTTPS with the Secure attribute (set above). Front-end JS keeps working: it reads the CSRF
# cookie name from a <meta> tag rather than hardcoding it (see assets/javascript/csrf.js).
SESSION_COOKIE_NAME = "__Secure-sessionid"
CSRF_COOKIE_NAME = "__Secure-csrftoken"

# HTTP Strict Transport Security
# https://docs.djangoproject.com/en/stable/ref/middleware/#http-strict-transport-security
# Starts at 60 seconds so a misconfigured deploy stays recoverable; raise SECURE_HSTS_SECONDS
# in the environment (e.g. 518400) once HTTPS is proven to work.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60)
# Keep these True only if every subdomain of this host is served over HTTPS.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

USE_HTTPS_IN_ABSOLUTE_URLS = True

# Email is configured in base.py: outside DEBUG it sends over SMTP via Resend, so all this
# environment needs is RESEND_API_KEY (plus a DEFAULT_FROM_EMAIL on a verified domain).
# Point EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER at another provider to switch.

ADMINS = ["achinga.chris@gmail.com"]

# Error tracking: initialised only when SENTRY_DSN is set, so deploys without Sentry run
# unchanged. sentry-sdk lives in the `prod` dependency group; the import stays behind this
# feature check because dev environments don't install it.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), RedisIntegration()],
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        # Performance tracing is off by default; set SENTRY_TRACES_SAMPLE_RATE=0.1 to sample 10%.
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
    )
