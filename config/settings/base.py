"""
Base Django settings for django-template project.

Shared settings imported by the environment-specific modules in this package:
`dev.py` (local development, the default) and `prod.py` (production).

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os
import sys
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy

# Build paths inside the project like this: BASE_DIR / "subdir".
# This file lives at config/settings/base.py, so the repo root is three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="django-insecure-2iEsfxzHLTfdRLJ3rpxS5iaBzQYMR1dXU6ZCfNaa")

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)
ENABLE_DEBUG_TOOLBAR = env.bool("ENABLE_DEBUG_TOOLBAR", default=False) and "test" not in sys.argv

# Note: It is not recommended to set ALLOWED_HOSTS to "*" in production
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    # >>> web
    "django.contrib.sitemaps",
    # <<< web
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # >>> web
    "django.forms",
    # <<< web
]

# Put your third-party apps here
THIRD_PARTY_APPS = [
    "allauth",  # allauth account/registration management
    "allauth.account",
    "allauth.socialaccount",
    "allauth.headless",
    # >>> web
    "django_htmx",
    # <<< web
    "rest_framework",
    "drf_spectacular",
]

# Put your project-specific apps here
PROJECT_APPS = [
    "apps.users.apps.UserConfig",
    "apps.web",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

# `apps.web` ships a custom `runserver` command (it auto-creates a dev superuser in DEBUG).
# Django resolves duplicate management commands to the app listed *earliest* in INSTALLED_APPS,
# so `apps.web` must come before `django.contrib.staticfiles`, which also defines `runserver`.
INSTALLED_APPS.remove("apps.web")
INSTALLED_APPS.insert(INSTALLED_APPS.index("django.contrib.staticfiles"), "apps.web")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # >>> web
    "django_htmx.middleware.HtmxMiddleware",
    # <<< web
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if ENABLE_DEBUG_TOOLBAR:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INSTALLED_APPS.append("debug_toolbar")
    INTERNAL_IPS = ["127.0.0.1"]
    try:
        import socket

        # get hostname for Docker environments
        # See https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#configure-internal-ips
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        # add discovered IPs plus some common defaults
        INTERNAL_IPS += [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["192.168.65.1", "10.0.2.2"]
    except OSError as e:
        print(f"{e} while attempting to resolve system hostname. Using INTERNAL_IPS={INTERNAL_IPS}")

    # `django-loginout-panel` adds a toolbar panel that toggles between the dev
    # superuser and an anonymous session in one click. Its endpoints 404 unless
    # DEBUG is on *and* the toolbar's show-callback passes, so it never exposes a
    # passwordless login outside local development.
    from debug_toolbar.settings import PANELS_DEFAULTS

    INSTALLED_APPS.append("loginout_panel")
    DEBUG_TOOLBAR_PANELS = ["loginout_panel.panel.LoginOutPanel", *PANELS_DEFAULTS]
    # The account to log in as. Matched against CustomUser.USERNAME_FIELD, which
    # is where `apps/web` runserver stores the dev superuser's email.
    LOGINOUT_USERNAME = env("DEV_SUPERUSER_EMAIL", default="admin@example.com")
    # Optional extra allowlist: restrict the endpoints to a single client IP.
    # Left unset by default so the panel keeps working from a Docker gateway IP.
    if env("LOGINOUT_SERVER", default=None):
        LOGINOUT_SERVER = env("LOGINOUT_SERVER")

# >>> web
# add browser reload only in debug mode
if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")
# <<< web

# add watchfiles only in debug mode
if DEBUG:
    INSTALLED_APPS.append("django_watchfiles")

ROOT_URLCONF = "config.urls"

# used to disable the cache in dev, but turn it on in production.
# more here: https://nickjanetakis.com/blog/django-4-1-html-templates-are-cached-by-default-with-debug-true
_DEFAULT_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

_CACHED_LOADERS = [("django.template.loaders.cached.Loader", _DEFAULT_LOADERS)]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # >>> web
                "apps.web.context_processors.project_meta",
                "apps.web.context_processors.csrf_settings",
                # <<< web
            ],
            "loaders": _DEFAULT_LOADERS if DEBUG else _CACHED_LOADERS,
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# >>> web
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
# <<< web

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

# Local development always uses SQLite (no Postgres/DATABASE_URL required).
# Production overrides this with Postgres in settings/prod.py.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Auth and Login

# Django recommends overriding the user model even if you don"t think you need to because it makes
# future changes much easier.
AUTH_USER_MODEL = "users.CustomUser"
# >>> web
LOGIN_URL = "account_login"
# <<< web
LOGIN_REDIRECT_URL = "/"

# Path prefix for the Django admin (must end in a slash). Override it in the environment
# (e.g. ADMIN_URL="manage-xyz/") to move the admin off /admin/ and cut automated scanning noise.
ADMIN_URL = env("ADMIN_URL", default="admin/")

# Argon2 is Django's recommended password hasher. Keeping PBKDF2 & co. in the list means
# existing password hashes still verify and are upgraded to Argon2 on each user's next login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Allauth setup

ACCOUNT_ADAPTER = "apps.users.adapter.EmailAsUsernameAdapter"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]

ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False  # don't send "forgot password" emails to unknown accounts
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_UNIQUE_EMAIL = True
# This configures a honeypot field to prevent bots from signing up.
# The ID strikes a balance of "realistic" - to catch bots,
# and "not too common" - to not trip auto-complete in browsers.
# You can change the ID or remove it entirely to disable the honeypot.
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = "phone_number_x"
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_USER_DISPLAY = lambda user: user.get_display_name()  # noqa: E731

# >>> web
ACCOUNT_FORMS = {
    "signup": "apps.users.forms.TermsSignupForm",
}
# <<< web

# User signup configuration: change to "mandatory" to require users to confirm email before signing in.
# or "optional" to send confirmation emails but not require them
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# allauth headless exposes signup, login, email verification etc. as a JSON API under /_allauth/
# for SPAs ("browser" client, cookie session) and mobile apps ("app" client, X-Session-Token header).
# With HEADLESS_ONLY, Django serves no account pages, so links in emails point at the front end.
# >>> web
HEADLESS_ONLY = False
# <<< web
# api-only: HEADLESS_ONLY = True
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
HEADLESS_FRONTEND_URLS = (
    {
        "account_confirm_email": f"{FRONTEND_URL}/account/verify-email/{{key}}",
        "account_reset_password": f"{FRONTEND_URL}/account/password/reset",
        "account_reset_password_from_key": f"{FRONTEND_URL}/account/password/reset/key/{{key}}",
        "account_signup": f"{FRONTEND_URL}/account/signup",
        "socialaccount_login_error": f"{FRONTEND_URL}/account/provider/callback",
    }
    if HEADLESS_ONLY
    else {}
)
# Serves the auth API's OpenAPI spec at /_allauth/openapi.html (and .json/.yaml).
HEADLESS_SERVE_SPECIFICATION = DEBUG
# >>> web

# For turnstile captchas
TURNSTILE_KEY = env("TURNSTILE_KEY", default=None)
TURNSTILE_SECRET = env("TURNSTILE_SECRET", default=None)
# <<< web


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_ROOT = BASE_DIR / "static_root"
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # swap these to use manifest storage to bust cache when files change
        # note: this may break image references in sass/css files which is why it is not enabled by default
        # "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

# future versions of Django will use BigAutoField as the default, but it can result in unwanted library
# migration files being generated, so we stick with AutoField for now.
# change this to BigAutoField if you"re sure you want to use it and aren"t worried about migrations.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Email setup

# default email used by your server
SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@localhost:8000")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="achinga.chris@gmail.com")

# Outbound mail is sent over SMTP, defaulting to Resend (https://resend.com).
#
# In DEBUG, emails are printed to the terminal instead of being sent: local development needs
# no credentials, and a stray password reset can never reach a real inbox. Everywhere else the
# SMTP backend is used. Set EMAIL_BACKEND explicitly to override either default.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend"
    ),
)

# Resend's SMTP endpoint expects the literal username "resend" and an API key ("re_...") as the
# password. Any other SMTP provider works too — override the host/port/user in the environment.
EMAIL_HOST = env("EMAIL_HOST", default="smtp.resend.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="resend")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=env("RESEND_API_KEY", default=""))
# Port 587 uses STARTTLS. To use implicit TLS instead, set EMAIL_PORT=465 and EMAIL_USE_SSL=True;
# EMAIL_USE_TLS then defaults to False, since Django rejects both being enabled at once.
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=not EMAIL_USE_SSL)
# Don't let a hanging SMTP connection tie up a request or worker indefinitely.
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

EMAIL_SUBJECT_PREFIX = "[django-template] "

# Django sites

SITE_ID = 1

# DRF config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        # Lets app clients call DRF views with the X-Session-Token issued by allauth headless.
        "allauth.headless.contrib.rest_framework.authentication.XSessionTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
}


SPECTACULAR_SETTINGS = {
    "TITLE": "django-template",
    "DESCRIPTION": "my django template",  # noqa: E501
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "displayOperationId": True,
    },
}
# Redis and cache setup
# `or` treats an empty REDIS_URL as unset so it falls back instead of yielding an empty URL
REDIS_URL = env("REDIS_URL", default=None) or env("REDIS_TLS_URL", default=None)
if not REDIS_URL:
    REDIS_HOST = env("REDIS_HOST", default="localhost")
    REDIS_PORT = env("REDIS_PORT", default="6379")
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

DUMMY_CACHE = {
    "BACKEND": "django.core.cache.backends.dummy.DummyCache",
}
REDIS_CACHE = {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": REDIS_URL,
}
CACHES = {
    "default": DUMMY_CACHE if DEBUG else REDIS_CACHE,
}

# Background tasks use Django's built-in tasks framework (django.tasks): define tasks with
# `@django.tasks.task` and call `.enqueue()`. The immediate backend runs them synchronously in
# the calling process, which needs no broker or worker. When real background work arrives,
# swap in a worker-backed backend (e.g. django-tasks' DatabaseBackend) here. Django ships no
# scheduler; run periodic work as management commands from cron.
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    },
}


# Pegasus config

# replace any values below with specifics for your project
PROJECT_METADATA = {
    "NAME": gettext_lazy("django-starter"),
    "URL": "http://localhost:8000",
    "DESCRIPTION": gettext_lazy("Django Starter Project Template"),  # noqa: E501
    "IMAGE": "images/web/cdc_logo.jpg",
    "KEYWORDS": "SaaS, django",
    "CONTACT_EMAIL": "achinga.chris@gmail.com",
}

# set this to True in production to have URLs generated with https instead of http
USE_HTTPS_IN_ABSOLUTE_URLS = env.bool("USE_HTTPS_IN_ABSOLUTE_URLS", default=False)

ADMINS = ["achinga.chris@gmail.com"]
# >>> web

# Umami website ID used by the shared site analytics script.
UMAMI_WEBSITE_ID = env("UMAMI_WEBSITE_ID", default="")
# <<< web


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": '[{asctime}] {levelname} "{name}" {message}',
            "style": "{",
            "datefmt": "%d/%b/%Y %H:%M:%S",  # match Django server time format
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "apps": {
            "handlers": ["console"],
            "level": env("CHRISDEVCODE_LOG_LEVEL", default="INFO"),
        },
        "pegasus": {
            "handlers": ["console"],
            "level": env("PEGASUS_LOG_LEVEL", default="DEBUG"),
        },
    },
}
