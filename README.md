# ChrisDevCode Django Project Starter Template

> Django (Server Only) starter template, built with [SaaS Pegasus](https://www.saaspegasus.com/).

This project runs in **two distinct modes**:

| Mode | How it runs | Database | Cache / broker | Celery | Used for |
|------|-------------|----------|----------------|--------|----------|
| **Local** | Natively on your machine via [uv](https://docs.astral.sh/uv/) + `npm` | SQLite (`db.sqlite3`) | DummyCache (no Redis needed) | Eager (synchronous) | Day-to-day development |
| **Production** | Docker Compose (Postgres + Redis + web + Vite + Celery) | Postgres | Redis | Real worker + beat | Containerized / deployed stack |

The split is driven by `DEBUG` and a few environment variables — see [Configuration](#configuration). You do
**not** need Docker for everyday development.

---

## Table of contents

- [Local development](#local-development)
  - [Prerequisites](#prerequisites)
  - [1. Bootstrap](#1-bootstrap-make-init)
  - [2. Admin user](#2-admin-user-automatic)
  - [3. Run the app (two processes)](#3-run-the-app-two-processes)
  - [4. Open it](#4-open-it)
- [Everyday commands](#everyday-commands)
- [Database](#database)
- [Front end](#front-end)
- [Generating the API client](#generating-the-api-client)
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

### 3. Run the app (two processes)

Local development needs **two terminals running simultaneously** — the Django server *and* the Vite
front-end server. In `DEBUG`, CSS/JS are served by Vite, so **if you skip the second process the page
loads unstyled.**

**Terminal 1 — Django backend (port 8000):**

```bash
make start
```

**Terminal 2 — Vite front end (port 5173):**

```bash
make npm-dev
```

### 4. Open it

Visit **[http://localhost:8000](http://localhost:8000/)** — you should see a fully styled page. The
Django admin is at [http://localhost:8000/admin/](http://localhost:8000/admin/) (log in with the
auto-created dev superuser from step 2).

> **Styles not loading?** It almost always means the Vite dev server (step 3, Terminal 2) isn't
> running, or `node_modules` is missing. Run `make npm-install` then `make npm-dev` and refresh.

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
| `make npm-dev` | Run the Vite dev server |
| `make npm-build` | Build production front-end assets |

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

JavaScript/TypeScript lives in `assets/` and is bundled by [Vite](https://vitejs.dev/) and served
through [`django-vite`](https://github.com/MrBin99/django-vite). Tailwind v4 + DaisyUI provide styling.

```bash
make npm-install            # install all npm packages
make npm-install <package>  # install a specific package
make npm-dev                # Vite dev server with hot reload (local development)
make npm-build              # build optimized assets (production)
make npm-type-check         # TypeScript type checking
```

In `DEBUG`, `DJANGO_VITE["default"]["dev_mode"]` is `True`, so assets are served live from the Vite
dev server. With `DEBUG=False`, Django serves the built manifest from `npm-build` instead.

---

## Generating the API client

The REST API (Django Rest Framework) publishes an OpenAPI schema via `drf-spectacular` at
`/api/schema/`. The TypeScript client in `api-client/` is **generated from that schema** and consumed
by the front end (see `assets/javascript/api.js`). It is generated code — don't edit it by hand.

Whenever you add or change API endpoints, regenerate the client:

```bash
make generate-api-client
```

This target:

1. Exports the OpenAPI schema from Django (`manage.py spectacular`).
2. Runs [OpenAPI Generator](https://openapi-generator.tech) (`typescript-fetch`), pinned to the
   version in `OPENAPI_GENERATOR_VERSION` (kept in sync with `api-client/.openapi-generator/VERSION`),
   via `npx @openapitools/openapi-generator-cli`.
3. Writes the result into `api-client/` and cleans up the temporary schema file.

**Requirements:** `node`/`npx` and a Java runtime (the generator runs on the JVM). Review the diff
before committing.

---

## Celery & background tasks

Celery runs background and scheduled tasks. **Locally, tasks run eagerly (synchronously)** by default
(`CELERY_TASK_ALWAYS_EAGER` defaults to `DEBUG`), so **no broker is required**.

To exercise the real worker locally, run a Redis instance, set `REDIS_URL` in `.env`, then:

```bash
make celery
# or directly:
uv run celery -A chrisdevcode worker -l INFO --beat --pool=solo
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
| `DEBUG` | `True` | Debug mode. **Must be `False` in production** (or use `settings_production`). |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hosts. Restrict in production. |
| `DATABASE_URL` | *(unset → SQLite)* | Postgres connection string in production. |
| `REDIS_URL` | *(unset → `redis://localhost:6379/0`)* | Cache + Celery broker. Required in production. |
| `CELERY_TASK_ALWAYS_EAGER` | `= DEBUG` | Run tasks synchronously when true. |
| `DEV_SUPERUSER_EMAIL` / `DEV_SUPERUSER_PASSWORD` | `admin@example.com` / `admin` | Auto-created dev superuser (DEBUG only). |
| `ENABLE_DEBUG_TOOLBAR` | `False`¹ | Django Debug Toolbar (disabled during tests). |
| `EMAIL_BACKEND` | console backend | Email backend; configure a real one (e.g. Mailgun/Anymail) in production. |
| `DJANGO_PORT` / `DJANGO_VITE_PORT` | `8000` / `5173` | Dev server ports. |
| `POSTGRES_PORT` / `REDIS_PORT` | `5432` / `6379` | Docker service ports. |
| `TURNSTILE_KEY` / `TURNSTILE_SECRET` | *(empty)* | Cloudflare Turnstile keys (optional). |
| `GOOGLE_ANALYTICS_ID` | *(empty)* | GA measurement ID (optional). |

¹ `.env.example` ships with `ENABLE_DEBUG_TOOLBAR=True` for convenience.

> Never commit `.env` — it's git-ignored. See `.env.example` for the full, annotated list.

**Settings modules:**

- `chrisdevcode.settings` — the default, used everywhere unless overridden. `DEBUG` defaults to `True`.
- `chrisdevcode.settings_production` — imports everything from `settings`, then forces `DEBUG=False`
  and enables the security hardening (SSL redirect, secure cookies, HSTS scaffolding, etc.). Select it
  in production via `DJANGO_SETTINGS_MODULE=chrisdevcode.settings_production`.

---

## Production

Docker Compose runs the full containerized stack — **Postgres, Redis, web, Vite, and a Celery worker
(with beat)**. The relevant `make` targets are prefixed with `prod-`:

```bash
make prod-build                    # build the docker images
make prod-start                    # start the stack (foreground)
make prod-start-bg                 # start the stack (background)
make prod-stop                     # stop the stack
make prod-restart                  # stop + start
make prod-ssh                      # shell into the running web container
make prod-manage ARGS='migrate'    # run a manage.py command in the web container
```

**Requirements:** [Docker](https://www.docker.com/get-started) and
[Docker Compose](https://docs.docker.com/compose/install).

### What the stack contains

`docker-compose.yml` defines five services:

| Service | Image / build | Role |
|---------|---------------|------|
| `db` | `postgres:17` | Postgres database (persisted in the `postgres_data` volume) |
| `redis` | `redis` | Cache + Celery broker (persisted in `redis_data`) |
| `web` | `Dockerfile.dev` | Django app on port `8000` |
| `vite` | `Dockerfile.vite` | Vite asset server on port `5173` |
| `celery` | `Dockerfile.dev` | Celery worker + beat |

`MY_UID` / `MY_GID` (in the `Makefile`) set the container user/group so files created in mounted
volumes belong to your host user rather than `root`. The defaults (`1000`) suit most setups.

### Configuring a real deployment

The compose stack boots the full multi-service topology, but for a hardened production deployment you
should:

1. **Use the production settings module:** set `DJANGO_SETTINGS_MODULE=chrisdevcode.settings_production`
   (forces `DEBUG=False` + security headers).
2. **Set required environment variables** in the deployment environment (or `.env`):
   - `SECRET_KEY` — a strong, unique secret.
   - `ALLOWED_HOSTS` — your real domain(s), not `*`.
   - `DATABASE_URL` — your Postgres instance.
   - `REDIS_URL` — your Redis instance (cache + Celery broker).
   - A real `EMAIL_BACKEND` and its credentials (e.g. Mailgun via Anymail — see `.env.example`).
3. **Build & collect static assets:** run `make npm-build`, then `collectstatic`
   (`make prod-manage ARGS='collectstatic --noinput'`). Static files are written to `static_root/`.
4. **Apply migrations:** `make prod-manage ARGS='migrate'`.
5. **Serve via a WSGI server.** `gunicorn` is included as a dependency; point it at
   `chrisdevcode.wsgi` behind a reverse proxy that terminates TLS (the production settings expect the
   `X-Forwarded-Proto` header).

Validate your configuration before going live:

```bash
make prod-manage ARGS='check --deploy'
```

---

*Built with [SaaS Pegasus](https://www.saaspegasus.com/), the Django SaaS boilerplate.*
