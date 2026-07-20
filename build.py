"""
Vercel build script (declared under [tool.vercel.scripts] in pyproject.toml).

Runs migrations when a database is reachable.

Note: Front-end assets are expected to be pre-built and committed to the
repository. Vercel's Python build environment does not include Node.js, so
`npm run build` cannot run here. Re-build assets locally with `make npm-build`
before deploying.

collectstatic is skipped because static files are already committed to git
for serverless deploys, and `config.settings.prod` requires DATABASE_URL
at import time which may not be available during the build phase.
"""

import os
import subprocess
import sys


def run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, **kwargs)


def main():
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.prod")}

    if os.environ.get("DATABASE_URL"):
        print("DATABASE_URL found - running migrations...")
        run([sys.executable, "manage.py", "migrate", "--noinput"], env=env)
    else:
        print("DATABASE_URL not set - skipping migrations (run them manually after attaching a database).")


if __name__ == "__main__":
    main()
