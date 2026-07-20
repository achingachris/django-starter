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
from typing import Any

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
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.forms",
]

# Put your third-party apps here
THIRD_PARTY_APPS = [
    "allauth",  # allauth account/registration management
    "allauth.account",
    "allauth.socialaccount",
    "django_htmx",
    "django_vite",
    "rest_framework",
    "drf_spectacular",
    "celery_progress",
    "waffle",
    "django_celery_beat",
]

# Put your project-specific apps here
PROJECT_APPS = [
    "apps.users.apps.UserConfig",
    "apps.services.apps.ServicesConfig",
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
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "waffle.middleware.WaffleMiddleware",
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

# add browser reload only in debug mode
if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

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
                "apps.web.context_processors.project_meta",
                "apps.web.context_processors.csrf_settings",
                # this line can be removed if not using google analytics
                "apps.web.context_processors.google_analytics_id",
            ],
            "loaders": _DEFAULT_LOADERS if DEBUG else _CACHED_LOADERS,
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

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
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"

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

ACCOUNT_FORMS = {
    "signup": "apps.users.forms.TermsSignupForm",
}

# User signup configuration: change to "mandatory" to require users to confirm email before signing in.
# or "optional" to send confirmation emails but not require them
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# For turnstile captchas
TURNSTILE_KEY = env("TURNSTILE_KEY", default=None)
TURNSTILE_SECRET = env("TURNSTILE_SECRET", default=None)


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

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

# Vite Integration
DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool("DJANGO_VITE_DEV_MODE", default=DEBUG),
        "dev_server_host": env("DJANGO_VITE_HOST", default="localhost"),
        "dev_server_port": env.int("DJANGO_VITE_PORT", default=5173),
        "manifest_path": BASE_DIR / "static" / ".vite" / "manifest.json",
    }
}

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

# future versions of Django will use BigAutoField as the default, but it can result in unwanted library
# migration files being generated, so we stick with AutoField for now.
# change this to BigAutoField if you"re sure you want to use it and aren"t worried about migrations.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Removes deprecation warning for future compatibility.
# see https://adamj.eu/tech/2023/12/07/django-fix-urlfield-assume-scheme-warnings/ for details.
FORMS_URLFIELD_ASSUME_HTTPS = True

# Email setup

# default email used by your server
SERVER_EMAIL = env("SERVER_EMAIL", default="vicmutua254@gmail.com")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="vicmutua254@gmail.com")

# SMTP configuration (Gmail by default). All values can be overridden from the
# environment / .env file. Gmail requires an *App Password* in EMAIL_HOST_PASSWORD.
# For local development without SMTP credentials, set:
#   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="vicmutua254@gmail.com")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# Dev convenience: Gmail rejects SMTP logins without an App Password, which would break
# the OTP flows on a fresh clone. When DEBUG is on and no SMTP password is configured,
# fall back to the console backend so verification codes are printed in the runserver
# terminal instead of being e-mailed. Set EMAIL_HOST_PASSWORD to send real e-mails.
if DEBUG and EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    print(
        "\n  [email] EMAIL_HOST_PASSWORD is empty — using the console e-mail backend."
        "\n  [email] OTP codes will be printed in this terminal. Set EMAIL_HOST_PASSWORD"
        "\n  [email] (a Gmail App Password) in .env to send real e-mails.\n"
    )

# Most production backends will require further customization. The below example uses Mailgun.
# ANYMAIL = {
#     "MAILGUN_API_KEY": env("MAILGUN_API_KEY", default=None),
#     "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN", default=None),
# }

# use in production
# see https://github.com/anymail/django-anymail for more details/examples
# EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

EMAIL_SUBJECT_PREFIX = "[Sokoni] "

# Secret shared with Vercel Cron Jobs: required in production for the HTTP cron endpoint
# (internal/cron/booking-reminders/). Generate a random value and set it as a Vercel env var.
CRON_SECRET = env("CRON_SECRET", default="")

# OTP (one-time-passcode) authentication settings -------------------------------------------
# Used by the e-mail OTP flows in apps.users (signup verification, sign-in codes,
# and password resets). Codes are e-mailed automatically when a flow form is submitted.
OTP_CODE_LENGTH = env.int("OTP_CODE_LENGTH", default=6)
OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=10)
OTP_MAX_VERIFY_ATTEMPTS = env.int("OTP_MAX_VERIFY_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)

# Django sites

SITE_ID = 1

# DRF config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
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
# Redis, cache, and/or Celery setup
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

CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Run tasks synchronously when there's no broker available (e.g. native local dev without Redis).
# Defaults to eager in DEBUG so the app works out of the box; production (DEBUG=False) uses the broker.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True

# Add tasks to this dict and run `python manage.py bootstrap_celery_tasks` to create them
from celery import schedules  # noqa: E402

SCHEDULED_TASKS: dict[str, Any] = {
    # e-mail clients & providers the day before a confirmed booking
    "hourly-booking-reminders": {
        "task": "apps.services.tasks.send_booking_reminders",
        "schedule": schedules.crontab(minute=0),
    },
}


# Pegasus config

# replace any values below with specifics for your project
PROJECT_METADATA = {
    "NAME": gettext_lazy("Sokoni"),
    "URL": "http://localhost:8000",
    "DESCRIPTION": gettext_lazy(
        "Kenya's service marketplace — book trusted local pros in minutes, or list your services and get booked."
    ),
    "IMAGE": "https://upload.wikimedia.org/wikipedia/commons/2/20/PEO-pegasus_black.svg",
    "KEYWORDS": "service marketplace, bookings, appointments, kenya",
    "CONTACT_EMAIL": "vicmutua254@gmail.com",
}

# set this to True in production to have URLs generated with https instead of http
USE_HTTPS_IN_ABSOLUTE_URLS = env.bool("USE_HTTPS_IN_ABSOLUTE_URLS", default=False)

ADMINS = ["achinga.chris@gmail.com"]

# Add your google analytics ID to the environment to connect to Google Analytics
GOOGLE_ANALYTICS_ID = env("GOOGLE_ANALYTICS_ID", default="")


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
