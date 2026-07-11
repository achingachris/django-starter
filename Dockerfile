# syntax=docker/dockerfile:1.5
#
# Production image for the Django app.
#
# Stage 1 compiles the front-end assets with Vite (into ./static, alongside the
# committed images/favicons). Stage 2 installs the production Python dependencies
# and copies the built assets in, then runs the app under gunicorn.

# ---------------------------------------------------------------------------
# Stage 1: build front-end assets
# ---------------------------------------------------------------------------
FROM node:24-bookworm AS frontend

WORKDIR /code

# Install JS deps against the lockfile for reproducible builds.
COPY package.json package-lock.json ./
RUN npm ci

# Build the assets. `vite build` reads assets/, vite.config.ts and tailwind.config.js
# and writes hashed bundles + manifest.json into /code/static.
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python application
# ---------------------------------------------------------------------------
FROM python:3.14-bookworm AS app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PROJECT_ENVIRONMENT=/home/django/.venv \
    PATH="/home/django/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# OS-level dependencies:
#   gettext   - translation compilation
#   libpq-dev - build + runtime headers for psycopg[c] (the compiled Postgres driver)
RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -yqq --no-install-recommends \
      gettext \
      libpq-dev

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

ARG MY_UID=1000
ARG MY_GID=1000
# create user and group (or update if they already exist)
RUN groupadd -g $MY_GID -r django || \
  (groupmod -g $MY_GID django 2>/dev/null || true) && \
  useradd -u $MY_UID -r -g django -m -d /home/django django 2>/dev/null || \
  usermod -u $MY_UID -g django -d /home/django django

RUN mkdir /code && chown django:django /code
WORKDIR /code
RUN mkdir -p /tmp/uv-cache && chown django:django /tmp/uv-cache

USER django

# Install production Python dependencies only (skip the dev group, add the prod group:
# gunicorn, psycopg[c], whitenoise). Cached on the dependency files alone.
COPY --chown=django:django uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/tmp/uv-cache,uid=$MY_UID,gid=$MY_GID \
    uv sync --frozen --no-dev --group prod

# Copy the application source.
COPY --chown=django:django . /code/

# Overlay the front-end assets built in stage 1 (bundles + manifest.json).
COPY --from=frontend --chown=django:django /code/static /code/static

EXPOSE 8000

# Default to gunicorn; compose overrides this for the web/celery services.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
