# Sokoni — Service Marketplace

> **Sokoni** ("at the market" — Swahili) is a Django service-marketplace app: clients book
> appointments with local service providers, providers list and manage their services.
> It includes OTP-based e-mail auth, role dashboards, HTMX interactions, a DRF API,
> and Celery booking reminders.
> Brand: coastal teal `#0d7a6f` + amber `#f59e0b`, Inter type, custom daisyUI themes
> `sokoni` (light) and `sokoni-dark` — dark mode follows your OS preference or the
> sun/moon toggle in the navbar (choice persisted in localStorage).
> Based on a Django starter template inherited from [SaaS Pegasus](https://www.saaspegasus.com/).

## How it works

The project runs in **two modes**:

| Mode | How it runs | Database | Cache / broker | Celery |
|------|-------------|----------|----------------|--------|
| **Local** | Natively via `uv` + `npm` | SQLite | DummyCache (no Redis) | Eager (synchronous) |
| **Production** | Docker Compose | Postgres | Redis | Real worker + beat |

The split is driven by `DEBUG` and environment variables. You do **not** need Docker for development.

## Quick start

```bash
make init      # install deps, create DB, apply migrations
make start     # Terminal 1: Django dev server (http://localhost:8000)
make npm-dev   # Terminal 2: Vite front-end dev server
```

`make` with no arguments lists all available commands.

## Key features

- **OTP-based auth**: signup, sign-in (password or code), password reset — all email-based with 6-digit codes
- **Service marketplace**: clients browse/book services; providers manage listings and confirm bookings
- **HTMX interactions**: live search, modals, and dynamic updates without full page reloads
- **REST API**: DRF with OpenAPI schema; auto-generated TypeScript client in `api-client/`
- **Background tasks**: Celery reminders sent 24h before confirmed bookings
- **Dark mode**: persisted in localStorage, follows OS preference by default

## Tech stack

- **Backend**: Django, Django REST Framework, Celery, django-allauth, drf-spectacular
- **Frontend**: HTMX, Alpine.js, Tailwind v4, DaisyUI, Vite, TypeScript
- **Database**: SQLite (local), Postgres (production)
- **Cache / Broker**: DummyCache (local), Redis (production)

## Configuration

Local config lives in `.env` (git-ignored). Copy from `.env.example`:

```bash
make setup-env       # local
make setup-env-prod  # production
```

Key variables: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL`, `EMAIL_HOST_PASSWORD` (Gmail App Password for OTP emails).

## Production

### Docker Compose

```bash
make prod-build      # build Docker image
make prod-start      # run stack (foreground)
make prod-start-bg   # run stack (background)
make prod-stop       # stop containers
```

Stack: Postgres, Redis, gunicorn web server, Celery worker. Settings module: `config.settings.prod`.

### Vercel (serverless)

Front-end assets must be pre-built and committed before deploying:

```bash
npm run build        # build assets into static/
git add static/ && git commit -m "chore: rebuild front-end assets"
git push             # triggers Vercel deploy
```

Configure environment variables in Vercel: `DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY`, `EMAIL_HOST_PASSWORD`, `ALLOWED_HOSTS`, `DATABASE_URL` (set automatically with Postgres integration), and `CRON_SECRET` (for booking reminders).

## Testing & quality

```bash
make test            # run tests
make ruff            # format + lint
make type-check      # mypy
```
