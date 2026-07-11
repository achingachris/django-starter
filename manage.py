#!/usr/bin/env -S uv run
import os
import sys
import warnings

# Silence version-check warnings from requests until it releases a compatible version
warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
