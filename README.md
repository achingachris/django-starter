# Django Project Starter Template

> Django 6.1 starter template on Python 3.14.

It ships a custom user model, [django-allauth][] (with a JSON auth API via
allauth headless), Django REST Framework with an OpenAPI schema, and Django's built-in tasks framework.
<!-- >>> web -->
The web front end is server-rendered Django templates with HTMX, Alpine.js and Tailwind CSS 4.
<!-- <<< web -->

This project runs in **two distinct modes**:

| Mode | How it runs | Database | Cache | Used for |
|------|-------------|----------|-------|----------|
| **Local** | Natively on your machine via [uv][] | SQLite (`db.sqlite3`) | DummyCache (no Redis needed) | Day-to-day development |
| **Production** | Docker Compose (Postgres + Redis + web) | Postgres | Redis | Containerized / deployed stack |

The split is driven by `DEBUG` and a few environment variables — see [Configuration](#configuration). You do
**not** need Docker for everyday development.

---

<!-- >>> starter -->
## Create a new project

Generate a fresh project from this template with the
[`django-starter-cdc`][django-starter-cdc] CLI instead of cloning the repo
(needs [uv][]):

```bash
uvx django-starter-cdc new myproject          # full setup: templates, HTMX, Alpine.js, Tailwind
uvx django-starter-cdc new myproject --api    # API only: DRF + allauth headless, no templates or npm
```

| | Full (default) | API only (`--api`) |
|---|---|---|
| Django templates, HTMX, Alpine.js, Tailwind | ✅ | — |
| allauth account pages (login, signup, profile) | ✅ | — |
| Node.js / npm needed | ✅ | — |
| allauth headless JSON auth API | ✅ | ✅ (`HEADLESS_ONLY = True`) |
| DRF + OpenAPI schema, `/api/users/me/` | ✅ | ✅ |
| SQLite locally, Docker Compose (Postgres + Redis) in production | ✅ | ✅ |

Prefer pip? Install it into a Python 3.14 virtual environment with `python -m pip install django-starter-cdc`
and run `django-starter-cdc new myproject`. The generated project still uses uv.

The project is renamed, gets a fresh `SECRET_KEY` in `.env` and a new git repository, and `make init` runs
for you. See [`cli/README.md`][cli-readme-md] for all options and install methods. You can also clone this repository
directly; it is the full variant.

---

<!-- <<< starter -->
## Table of contents

- [Local development](#local-development)
  - [Prerequisites](#prerequisites)
  - [1. Bootstrap](#1-bootstrap-make-init)
  - [2. Admin user](#2-admin-user-automatic)
  - [3. Run the app](#3-run-the-app)
  - [4. Open it](#4-open-it)
- [Everyday commands](#everyday-commands)
- [Database](#database)
- [API & authentication](#api--authentication)
<!-- >>> web -->
- [Front end](#front-end)
<!-- <<< web -->
- [Background tasks](#background-tasks)
- [Testing](#testing)
- [Code quality & git hooks](#code-quality--git-hooks)
- [Configuration](#configuration)
- [Production](#production)

---

## Local development

Local development runs **natively** on your Python environment (managed with
[uv][]) against a **SQLite** database. No Docker, Postgres, or Redis
required.

### Prerequisites

Install these once on your machine:

- **[uv][uv-install]** — manages the virtual environment
  and provisions Python 3.14 for you (you do **not** need to install Python 3.14 separately):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
  ```
<!-- >>> web -->
- **[Node.js][node-js] 20+** — provides `node` and `npm` for the front-end build.
<!-- <<< web -->
- **`make`** — preinstalled on macOS/Linux. On Windows,
  [follow these instructions][follow-these-instructions].

### 1. Bootstrap (`make init`)

From the project root:

```bash
make init
```

This single command:

1. Copies `.env.example` → `.env` (only if `.env` doesn't already exist).
2. Installs Python dependencies into a local `.venv` with `uv sync`.
<!-- >>> web -->
3. Installs front-end dependencies with `npm install`.
<!-- <<< web -->
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
([django-loginout-panel][]) toggles between this
superuser and an anonymous session in one click — handy for checking logged-out views. Its endpoints
are POST-only, CSRF-protected, and 404 unless `DEBUG` is on and the toolbar is visible.

### 3. Run the app

```bash
make start
```

<!-- >>> web -->
`make init` already built the CSS once. While you edit templates or styles, run the Tailwind watcher in a
second terminal so new utility classes get compiled:

```bash
make npm-dev
```
<!-- <<< web -->

### 4. Open it

<!-- >>> web -->
Visit **[http://localhost:8000][localhost]** — you should see a fully styled page.

> **Styles not loading?** `static/css/site.css` and `static/vendor/` are build outputs. Run
> `make npm-build` (or `make init`) to create them.

<!-- <<< web -->
| URL | What's there |
|-----|--------------|
| [/admin/][admin] | Django admin (log in with the dev superuser from step 2) |
| [/api/schema/swagger-ui/][api-schema-swagger-ui] | Your DRF endpoints (Swagger UI; ReDoc at `/api/schema/redoc/`) |
| [/_allauth/openapi.html][allauth-openapi-html] | The allauth headless auth API reference (`DEBUG` only) |

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

Management commands can also be run directly: `uv run python manage.py <command>`.
<!-- >>> web -->
The front-end targets (`make npm-dev`, `make npm-build`) are covered under [Front end](#front-end).
<!-- <<< web -->

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

## API & authentication

APIs are built with [Django REST Framework][django-rest-framework] and documented by
[drf-spectacular][] at `/api/schema/` (Swagger UI at
`/api/schema/swagger-ui/`, ReDoc at `/api/schema/redoc/`). DRF views require a logged-in user by
default (`IsAuthenticated`) and are paginated 100 per page. `GET /api/users/me/`
(`apps/users/api.py`) is a small example that returns the current user.

Authentication is [django-allauth][]. Its
[headless mode][headless-mode] exposes signup, login, email
verification, login codes and password reset as a JSON API under `/_allauth/`, in two flavours:

- **`app` client** (`/_allauth/app/v1/...`) for mobile and other non-browser clients. Login returns
  `meta.session_token`; send it as the `X-Session-Token` header on later requests. DRF accepts the same
  header, so one token works for both the auth API and your own endpoints.
- **`browser` client** (`/_allauth/browser/v1/...`) for single-page apps, using Django's session cookie
  and CSRF token. An SPA on another origin will also need
  [`django-cors-headers`][django-cors-headers].

```bash
curl -s -X POST http://localhost:8000/_allauth/app/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "admin@example.com", "password": "admin"}'

curl -s http://localhost:8000/api/users/me/ -H 'X-Session-Token: <session_token>'
```

`HEADLESS_ONLY` in `config/settings/base.py` decides whether Django also serves allauth's own account
pages. When it is on, links in account emails (verify email, reset password) point at your front end:
set `FRONTEND_URL` and adjust `HEADLESS_FRONTEND_URLS` to match its routes.
<!-- >>> web -->
Here it is off, so the regular pages (`/accounts/login/` etc.) keep working alongside the API.
<!-- <<< web -->

---

<!-- >>> web -->
## Front end

There is no JavaScript bundler. Styling is Tailwind v4 (plain utility classes, no component library)
compiled by the [Tailwind CLI][tailwind-cli] from
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

<!-- <<< web -->
## Background tasks

Background work uses Django's built-in tasks framework
([`django.tasks`][django-tasks]). Define a task with the
`@task` decorator and call `.enqueue()` on it. The configured backend is the **immediate** one, so
tasks run synchronously in the calling process: no broker, no worker, nothing extra to run locally
or in production.

When a real queue is needed, point `TASKS["default"]["BACKEND"]` in `config/settings/base.py` at a
worker-backed backend (for example the `DatabaseBackend` from the `django-tasks` package) and add
its worker as a Compose service. Django ships no scheduler; run periodic work as management
commands from cron.

---

## Testing

```bash
make test                                              # run everything
make test ARGS='apps.users.tests.test_api'             # a single module
make test ARGS='apps.users.tests.test_api --keepdb'    # reuse the test DB (faster)
```

On Linux you can re-run tests on change:

```bash
find . -name '*.py' | entr uv run python manage.py test --settings=config.settings.test apps.users.tests.test_api
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

The hooks run Ruff (format + lint), django-upgrade and the standard pre-commit checks
<!-- >>> web -->
plus djLint on the templates
<!-- <<< web -->
— see `.pre-commit-config.yaml`. CI runs the same hooks, mypy and the test suite.

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
| `REDIS_URL` | *(unset → `redis://localhost:6379/0`)* | Cache. Required in production. |
| `DEV_SUPERUSER_EMAIL` / `DEV_SUPERUSER_PASSWORD` | `admin@example.com` / `admin` | Auto-created dev superuser (DEBUG only). |
| `ENABLE_DEBUG_TOOLBAR` | `False`¹ | Django Debug Toolbar (disabled during tests). |
| `LOGINOUT_SERVER` | *(unset)* | Restrict the toolbar's "Login / out" panel to one client IP (optional). |
| `EMAIL_BACKEND` | console in `DEBUG`, else SMTP | Override to force a specific backend. |
| `RESEND_API_KEY` | *(empty)* | Resend API key, used as the SMTP password. Required to send real mail. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` | `smtp.resend.com` / `587` / `resend` | Override to use another SMTP provider. |
| `DJANGO_PORT` | `8000` | Dev server port. |
| `POSTGRES_PORT` / `REDIS_PORT` | `5432` / `6379` | Docker service ports. |
| `FRONTEND_URL` | `http://localhost:3000` | Front end that account-email links point at when `HEADLESS_ONLY` is on. |

¹ `.env.example` ships with `ENABLE_DEBUG_TOOLBAR=True` for convenience.

<!-- >>> web -->
The web front end also reads two optional variables: `UMAMI_WEBSITE_ID` (Umami site analytics) and
`TURNSTILE_KEY` / `TURNSTILE_SECRET` (Cloudflare Turnstile on the signup form).
<!-- <<< web -->

> Never commit `.env` — it's git-ignored. See `.env.example` for the full, annotated list.

**Settings modules:** live in the `config/settings/` package.

- `config.settings.base` — shared settings imported by both environment modules. Not selected directly.
- `config.settings.dev` — the default, used everywhere unless overridden. `DEBUG` defaults to `True`.
- `config.settings.prod` — imports everything from `base`, then forces `DEBUG=False`
  and enables the security hardening (SSL redirect, secure cookies, HSTS scaffolding, etc.). Select it
  in production via `DJANGO_SETTINGS_MODULE=config.settings.prod`.

**Email:** in `DEBUG`, messages are printed to the terminal running `make start` — no credentials
needed, and no chance of emailing a real person while developing. Outside `DEBUG`, mail is sent over
SMTP via [Resend][]; set `RESEND_API_KEY` and make sure `DEFAULT_FROM_EMAIL` is on
a domain you've verified there. Any other SMTP provider works by overriding `EMAIL_HOST`,
`EMAIL_PORT`, and `EMAIL_HOST_USER`. To check your setup:

```bash
make manage ARGS='send_test_email you@example.com'
```

To send real mail from local development, set `EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"`
and `RESEND_API_KEY` in `.env`.

---

## Production

Docker Compose runs a production-ready stack — **Postgres, Redis, and a gunicorn web server**.
The web service runs from one image built from `Dockerfile` with
`DJANGO_SETTINGS_MODULE=config.settings.prod`.
<!-- >>> web -->
It is a multi-stage build: the first stage compiles the CSS with the Tailwind CLI, the second installs
the production Python dependencies and copies the built assets in.
<!-- <<< web -->

**Requirements:** [Docker][] and
[Docker Compose][docker-compose].

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
[WhiteNoise][] — no separate web server is required (put a
TLS-terminating reverse proxy in front for HTTPS; the production settings honour the
`X-Forwarded-Proto` header).

### What the stack contains

`docker-compose.yml` defines three services:

| Service | Image / build | Role |
|---------|---------------|------|
| `db` | `postgres:17` | Postgres database (persisted in the `postgres_data` volume) |
| `redis` | `redis:7` | Cache (persisted in `redis_data`) |
| `web` | `Dockerfile` | Django app under gunicorn on port `8000` (runs migrate + collectstatic on boot) |

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

## Credits

This template was originally derived from [SaaS Pegasus][saas-pegasus], the Django SaaS
boilerplate, and has since been reworked (no Celery or Vite, an API-only variant). It is
released under the MIT license; see `LICENSE`.

<!-- References -->

[django-allauth]: https://docs.allauth.org/
[uv]: https://docs.astral.sh/uv/
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[follow-these-instructions]: https://stackoverflow.com/a/57042516/8207
[django-loginout-panel]: https://github.com/andytwoods/django-loginout-panel
[admin]: http://localhost:8000/admin/
[api-schema-swagger-ui]: http://localhost:8000/api/schema/swagger-ui/
[allauth-openapi-html]: http://localhost:8000/_allauth/openapi.html
[django-rest-framework]: https://www.django-rest-framework.org/
[drf-spectacular]: https://drf-spectacular.readthedocs.io/
[headless-mode]: https://docs.allauth.org/en/latest/headless/index.html
[resend]: https://resend.com
[docker]: https://www.docker.com/get-started
[docker-compose]: https://docs.docker.com/compose/install
[whitenoise]: https://whitenoise.readthedocs.io/
[saas-pegasus]: https://www.saaspegasus.com/
[django-cors-headers]: https://pypi.org/project/django-cors-headers/
[django-tasks]: https://docs.djangoproject.com/en/stable/topics/tasks/
<!-- >>> web -->
[node-js]: https://nodejs.org/
[localhost]: http://localhost:8000/
[tailwind-cli]: https://tailwindcss.com/docs/installation/tailwind-cli
<!-- <<< web -->
<!-- >>> starter -->
[django-starter-cdc]: https://pypi.org/project/django-starter-cdc/
[cli-readme-md]: cli/README.md
<!-- <<< starter -->
