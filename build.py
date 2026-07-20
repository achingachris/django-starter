"""
Vercel build script (declared under [tool.vercel.scripts] in pyproject.toml).

Runs `manage.py migrate` during the build when a database is reachable, so a
fresh deploy always has an up-to-date schema. When no DATABASE_URL is present
(e.g. a preview build without a database attached yet) the step is skipped —
the app still deploys, and you can run migrations later with:

    vercel env pull .env.local && python manage.py migrate
"""

import importlib
import os
import subprocess
import sys


def _ensure_psycopg_binary():
    """Guarantee a *precompiled* Postgres driver (Vercel images have no libpq).

    Vercel may install only pyproject.toml's main deps (plain `psycopg`), so we
    top up `psycopg[binary]` here when it's missing. Idempotent no-op when the
    binary wheel is already installed.
    """
    try:
        import psycopg_binary  # noqa: F401

        return
    except ImportError:
        pass
    import shutil

    uv = shutil.which("uv")
    cmd = (
        [uv, "pip", "install", "--python", sys.executable, "psycopg[binary]"]
        if uv
        else [sys.executable, "-m", "pip", "install", "psycopg[binary]"]
    )
    print("Installing precompiled Postgres driver (psycopg[binary])...")
    subprocess.run(cmd, check=False)


def main():
    _ensure_psycopg_binary()

    module = os.environ.get("DJANGO_SETTINGS_MODULE") or "config.settings.prod"

    # Check for a database BEFORE importing prod settings (prod.py hard-fails
    # on a missing DATABASE_URL). A build without one can still succeed — the
    # app just needs DATABASE_URL set for the runtime to work.
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL not set - skipping migrations.")
        print("WARN: the app needs DATABASE_URL (Vercel -> Settings -> Environment")
        print("Vars -> Production) or every request will fail at runtime.")
        return

    try:
        importlib.import_module(module)
    except ImportError as exc:
        sys.exit(
            f'\nERROR: DJANGO_SETTINGS_MODULE="{module}" could not be imported: {exc}\n'
            "It must be exactly: config.settings.prod  "
            "(Vercel -> Settings -> Environment Variables)"
        )

    print("DATABASE_URL found - running migrations...")
    subprocess.check_call(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        env={**os.environ, "DJANGO_SETTINGS_MODULE": module},
    )


if __name__ == "__main__":
    main()
