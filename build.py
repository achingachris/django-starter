"""
Vercel build script (declared under [tool.vercel.scripts] in pyproject.toml).

Runs `manage.py migrate` during the build when a database is reachable, so a
fresh deploy always has an up-to-date schema. When no DATABASE_URL is present
(e.g. a preview build without a database attached yet) the step is skipped —
the app still deploys, and you can run migrations later with:

    vercel env pull .env.local && python manage.py migrate
"""

import os
import subprocess
import sys


def main():
    if os.environ.get("DATABASE_URL"):
        print("DATABASE_URL found - running migrations...")
        subprocess.check_call(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            env={**os.environ, "DJANGO_SETTINGS_MODULE": os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.prod")},
        )
    else:
        print("DATABASE_URL not set - skipping migrations (run them manually after attaching a database).")


if __name__ == "__main__":
    main()
