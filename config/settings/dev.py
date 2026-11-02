# flake8: noqa: F405
"""Local development settings.

This is the default settings module (see manage.py / wsgi.py).
It inherits everything from base.py, which already defaults to a development-
friendly configuration (DEBUG=True, SQLite, dummy cache, immediate tasks). Add any
dev-only overrides below.
"""

from .base import *  # noqa F401
