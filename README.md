# Django Project Starter Template

> Django (Server Only) starter template, inherited from [SaaS Pegasus](https://www.saaspegasus.com/).

> 📌 New to this fork? See [**WHATS_NEW.md**](./WHATS_NEW.md) for the
> full user-flow / two-role / PWA additions on top of the base template,
> and [**DEPLOYMENT.md**](./DEPLOYMENT.md) to deploy it on a VPS.


This project runs in **two distinct modes**:

| Mode | How it runs | Database | Cache / broker | Celery | Used for |
|------|-------------|----------|----------------|--------|----------|
| **Local** | Natively on your machine via [uv](https://docs.astral.sh/uv/) (+ `npm` for the CSS build) | SQLite (`db.sqlite3`) | DummyCache (no Redis needed) | Eager (synchronous) | Day-to-day development |
| **Production** | Docker Compose (Postgres + Redis + web + Celery) | Postgres | Redis | Real worker + beat | Containerized / deployed stack |

The split is driven by `DEBUG` and a few environment variables — see [Configuration](#configuration). You do
**not** need Docker for everyday development.

---

## Table of contents

- [Local development](#local-development)
  - [Prerequisites](#prerequisites)
  - [1. Bootstrap](#1-bootstrap-make-init)
  - [2. Admin user](#2-admin-user-automatic)
  - [3. Run the app](#3-run-the-app)
  - [4. Open it](#4-open-it)
- [Everyday commands](#everyday-commands)
- [Database](#database)
- [Front end](#front-end)
- [Celery & background tasks](#celery--background-tasks)
- [Testing](#testing)
- [Code quality & git hooks](#code-quality--git-hooks)
- [Configuration](#configuration)
- [Production](#production)

---

## Local development

Local development runs **natively** on your Python environment (managed with
[uv](https://docs.astral.sh/uv/)) against a **SQLite** database. No Docker, Postgres, or Redis
required.

### Prerequisites

Install these once on your machine:

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — manages the virtual environment
  and provisions Python 3.14 for you (you do **not** need to install Python 3.14 separately):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
  ```
- **[Node.js](https://nodejs.org/) 20+** — provides `node` and `npm` for the front-end build.
- **`make`** — preinstalled on macOS/Linux. On Windows,
  [follow these instructions](https://stackoverflow.com/a/57042516/8207).

### 1. Bootstrap (`make init`)

From the project root:

```bash
make init
```

This single command:

1. Copies `.env.example` → `.env` (only if `.env` doesn't already exist).
2. Installs Python dependencies into a local `.venv` with `uv sync`.
3. Installs front-end dependencies with `npm install`.
4. Creates the SQLite database (`db.sqlite3`) and applies all migrations.

### 2. Admin user (automatic)

In `DEBUG`, `make start` (i.e. `runserver`) **automatically creates a development superuser** the
first time it runs, then silently skips it afterwards. Defaults:

| Field    | Value               |
|----------|---------------------|
| Email    | `admin@example.com` |
| Password | `admin`             |

Override via `DEV_SUPERUSER_EMAIL` / `DEV_SUPERUSER_PASSWORD` in `.env`. This only happens when
`DEBUG` is true, so production is never affected. You can still create more accounts with
`make manage ARGS='createsuperuser'`.

With `ENABLE_DEBUG_TOOLBAR=True`, the toolbar's **"Login / out"** panel
([django-loginout-panel](https://github.com/andytwoods/django-loginout-panel)) toggles between this
superuser and an anonymous session in one click — handy for checking logged-out views. Its endpoints
are POST-only, CSRF-protected, and 404 unless `DEBUG` is on and the toolbar is visible.

### 3. Run the app

```bash
make start
```

`make init` already built the CSS once. While you edit templates or styles, run the Tailwind watcher in a
second terminal so new utility classes get compiled:

```bash
make npm-dev
```

### 4. Open it

Visit **[http://localhost:8000](http://localhost:8000/)** — you should see a fully styled page. The
Django admin is at [http://localhost:8000/admin/](http://localhost:8000/admin/) (log in with the
auto-created dev superuser from step 2).

> **Styles not loading?** `static/css/site.css` and `static/vendor/` are build outputs. Run
> `make npm-build` (or `make init`) to create them.

New to Pegasus? [Try these next steps](https://docs.saaspegasus.com/getting-started/#post-installation-steps).

---

## Everyday commands

Run `make` with no arguments to list every available target. Local targets (`start`, `migrate`,
`test`, `shell`, …) run natively via `uv`; production targets are prefixed with `prod-` and use Docker.

| Command | What it does |
|---------|--------------|
| `make start` | Run the Django dev server |
| `make shell` | Open a Django Python shell |
| `make dbshell` | Open a database shell (SQLite locally) |
| `make manage ARGS='<cmd>'` | Run any `manage.py` command, e.g. `ARGS='createsuperuser'` |
| `make migrations` | Create new migrations |
| `make migrate` | Apply migrations |
| `make test` | Run the test suite |
| `make ruff` | Format **and** lint Python with Ruff |
| `make npm-dev` | Rebuild the CSS as templates change |
| `make npm-build` | Build the minified CSS and vendored JS/fonts |

Management commands can also be run directly: `uv run python manage.py <command>`.

---

## Database

Local development uses **SQLite** by default — no setup required. Leaving `DATABASE_URL` unset makes
Django use the `db.sqlite3` file in the project root.

```bash
make migrations   # uv run python manage.py makemigrations
make migrate      # uv run python manage.py migrate
```

In production, set `DATABASE_URL` (e.g. a Postgres connection string) in the environment — it takes
precedence over SQLite automatically.

---

## Front end

There is no JavaScript bundler. Styling is Tailwind v4 (plain utility classes, no component library)
compiled by the [Tailwind CLI](https://tailwindcss.com/docs/installation/tailwind-cli) from
`assets/styles/site.css` into `static/css/site.css`. htmx, Alpine.js and Font Awesome are npm
packages copied as-is into `static/vendor/` by the same build, and the site's own JavaScript is a
plain script at `static/javascript/site.js`. Templates load everything with `{% static %}`.

```bash
make npm-install            # install all npm packages
make npm-install <package>  # install a specific package
make npm-dev                # rebuild the CSS whenever templates change (local development)
make npm-build              # minified CSS + vendored libraries (production)
```

`static/css/` and `static/vendor/` are git-ignored build outputs; the Docker image builds them in its
first stage.

---

## Celery & background tasks

Celery runs background and scheduled tasks. **Locally, tasks run eagerly (synchronously)** by default
(`CELERY_TASK_ALWAYS_EAGER` defaults to `DEBUG`), so **no broker is required**.

To exercise the real worker locally, run a Redis instance, set `REDIS_URL` in `.env`, then:

```bash
make celery
# or directly:
uv run celery -A config worker -l INFO --beat --pool=solo
```

> The `solo` pool is fine for development but **not** for production.

In production (`DEBUG=False`) tasks dispatch to the Redis broker and are processed by the dedicated
`celery` container (see [Production](#production)).

---

## Testing

```bash
make test                                              # run everything
make test ARGS='apps.web.tests.test_basic_views'       # a single module
make test ARGS='apps.web.tests.test_basic_views --keepdb'  # reuse the test DB (faster)
```

On Linux you can re-run tests on change:

```bash
find . -name '*.py' | entr uv run python manage.py test apps.web.tests.test_basic_views
```

---

## Code quality & git hooks

```bash
make ruff           # ruff format + lint --fix
make ruff-format    # format only
make ruff-lint      # lint + autofix only
make type-check     # mypy
```

Install the pre-commit hooks (run automatically on every commit):

```bash
uv run pre-commit install --install-hooks
```

See the [Pegasus code-formatting docs](https://docs.saaspegasus.com/code-structure#code-formatting)
for details.

---

## Configuration

Configuration is read from environment variables (via `.env` locally). `make init` /
`make setup-env` copy `.env.example` → `.env` for you. The most important variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | insecure dev key | Django secret key. **Set a strong value in production.** |
| `DEBUG` | `True` | Debug mode. **Must be `False` in production** (or use `config.settings.prod`). |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts. Restrict in production. |
| `DATABASE_URL` | *(unset → SQLite)* | Postgres connection string in production. |
| `REDIS_URL` | *(unset → `redis://localhost:6379/0`)* | Cache + Celery broker. Required in production. |
| `CELERY_TASK_ALWAYS_EAGER` | `= DEBUG` | Run tasks synchronously when true. |
| `DEV_SUPERUSER_EMAIL` / `DEV_SUPERUSER_PASSWORD` | `admin@example.com` / `admin` | Auto-created dev superuser (DEBUG only). |
| `ENABLE_DEBUG_TOOLBAR` | `False`¹ | Django Debug Toolbar (disabled during tests). |
| `LOGINOUT_SERVER` | *(unset)* | Restrict the toolbar's "Login / out" panel to one client IP (optional). |
| `EMAIL_BACKEND` | console in `DEBUG`, else SMTP | Override to force a specific backend. |
| `RESEND_API_KEY` | *(empty)* | Resend API key, used as the SMTP password. Required to send real mail. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` | `smtp.resend.com` / `587` / `resend` | Override to use another SMTP provider. |
| `DJANGO_PORT` | `8000` | Dev server port. |
| `POSTGRES_PORT` / `REDIS_PORT` | `5432` / `6379` | Docker service ports. |
| `UMAMI_WEBSITE_ID` | *(empty)* | Umami website ID for site analytics (optional). |
| `TURNSTILE_KEY` / `TURNSTILE_SECRET` | *(empty)* | Cloudflare Turnstile keys (optional). |

¹ `.env.example` ships with `ENABLE_DEBUG_TOOLBAR=True` for convenience.

> Never commit `.env` — it's git-ignored. See `.env.example` for the full, annotated list.

**Settings modules:** live in the `config/settings/` package.

- `config.settings.base` — shared settings imported by both environment modules. Not selected directly.
- `config.settings.dev` — the default, used everywhere unless overridden. `DEBUG` defaults to `True`.
- `config.settings.prod` — imports everything from `base`, then forces `DEBUG=False`
  and enables the security hardening (SSL redirect, secure cookies, HSTS scaffolding, etc.). Select it
  in production via `DJANGO_SETTINGS_MODULE=config.settings.prod`.

**Email:** in `DEBUG`, messages are printed to the terminal running `make start` — no credentials
needed, and no chance of emailing a real person while developing. Outside `DEBUG`, mail is sent over
SMTP via [Resend](https://resend.com); set `RESEND_API_KEY` and make sure `DEFAULT_FROM_EMAIL` is on
a domain you've verified there. Any other SMTP provider works by overriding `EMAIL_HOST`,
`EMAIL_PORT`, and `EMAIL_HOST_USER`. To check your setup:

```bash
make manage ARGS='send_test_email you@example.com'
```

To send real mail from local development, set `EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"`
and `RESEND_API_KEY` in `.env`.

---

## Production

Docker Compose runs a production-ready stack — **Postgres, Redis, a gunicorn web server, and a
Celery worker (with beat)**. The web and Celery services share one image built from `Dockerfile`
(a multi-stage build that compiles the CSS with the Tailwind CLI, then installs the production
Python dependencies) and run with `DJANGO_SETTINGS_MODULE=config.settings.prod`.

**Requirements:** [Docker](https://www.docker.com/get-started) and
[Docker Compose](https://docs.docker.com/compose/install).

### 1. Configure secrets

```bash
make setup-env-prod    # copies .env.prod.example -> .env.prod (git-ignored)
```

Edit `.env.prod` and set real values — at minimum `SECRET_KEY`, `ALLOWED_HOSTS`,
`POSTGRES_PASSWORD` / `DATABASE_URL`, and `REDIS_URL`. `DEBUG=False` is required (see the notes in
the file). For email, set `RESEND_API_KEY` and point `DEFAULT_FROM_EMAIL` / `SERVER_EMAIL` at a
domain verified in Resend.

### 2. Build and run

```bash
make prod-build                    # build the production image
make prod-start                    # start the stack (foreground)
make prod-start-bg                 # start the stack (background)
make prod-stop                     # stop the stack
make prod-restart                  # stop + start
make prod-ssh                      # shell into the running web container
make prod-manage ARGS='migrate'    # run a manage.py command in the web container
```

On startup the `web` service **applies migrations and runs `collectstatic` automatically**, then
serves the app with gunicorn on port `8000`. Static files are served directly by the app via
[WhiteNoise](https://whitenoise.readthedocs.io/) — no separate web server is required (put a
TLS-terminating reverse proxy in front for HTTPS; the production settings honour the
`X-Forwarded-Proto` header).

### What the stack contains

`docker-compose.yml` defines four services:

| Service | Image / build | Role |
|---------|---------------|------|
| `db` | `postgres:17` | Postgres database (persisted in the `postgres_data` volume) |
| `redis` | `redis:7` | Cache + Celery broker (persisted in `redis_data`) |
| `web` | `Dockerfile` | Django app under gunicorn on port `8000` (runs migrate + collectstatic on boot) |
| `celery` | `Dockerfile` | Celery worker + beat |

Uploaded media persists in the `media_files` volume. `MY_UID` / `MY_GID` (in the `Makefile`) set the
container user/group so files created in mounted volumes belong to your host user rather than `root`.
The defaults (`1000`) suit most setups.

### Before going live

Validate the deployment settings:

```bash
make prod-manage ARGS='check --deploy'
```

Consider also enabling HSTS (see the commented block in `config/settings/prod.py`) once you're
confident HTTPS works, and scaling `GUNICORN_WORKERS` in `.env.prod` to `(2 × CPU cores) + 1`.

---

*Built with [SaaS Pegasus](https://www.saaspegasus.com/), the Django SaaS boilerplate.*
