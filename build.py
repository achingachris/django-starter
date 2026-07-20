"""
Vercel build script (declared under [tool.vercel.scripts] in pyproject.toml).

Builds front-end assets with Vite, collects static files, and runs migrations
when a database is reachable.
"""

import os
import shutil
import subprocess
import sys


def run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, **kwargs)


def main():
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.prod")}

    if shutil.which("npm"):
        run(["npm", "run", "build"])
    else:
        print("npm not found - skipping front-end build")

    run([sys.executable, "manage.py", "collectstatic", "--noinput"], env=env)

    if os.environ.get("DATABASE_URL"):
        print("DATABASE_URL found - running migrations...")
        run([sys.executable, "manage.py", "migrate", "--noinput"], env=env)
    else:
        print("DATABASE_URL not set - skipping migrations (run them manually after attaching a database).")


if __name__ == "__main__":
    main()
