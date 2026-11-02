# django-starter-cdc

Generate a new Django 6.1 project from [django-starter](https://github.com/achingachris/django-starter):
either a full-stack app (Django templates, HTMX, Alpine.js, Tailwind) or an API-only backend
(Django REST Framework + allauth headless).

The generator has no dependencies of its own. It needs Python 3.14, and the generated project uses
[uv](https://docs.astral.sh/uv/) (plus npm for the full variant).

## Usage

```bash
uvx django-starter-cdc new myproject          # full variant
uvx django-starter-cdc new myproject --api    # API-only variant
```

This downloads the django-starter release that matches the generator's version, renders the
chosen variant into `./myproject`, writes a `.env` with a fresh `SECRET_KEY`, runs `git init`
and then `make init` (installs dependencies and migrates the SQLite database). Then:

```bash
cd myproject
make start
```

and open <http://localhost:8000/admin/> and <http://localhost:8000/api/schema/swagger-ui/>.

### Options

```
django-starter-cdc new <name> [--api] [--email EMAIL] [--ref REF | --source PATH]
                              [--no-install] [--no-git] [--dir PATH]
```

| Option | What it does |
| --- | --- |
| `<name>` | Project name: a lowercase slug of letters, digits, `-` and `_` that starts with a letter. Used for the directory, the Python/npm package name and the `<NAME>_` env-var prefix. |
| `--api` | Generate the API-only variant (see below). |
| `--email EMAIL` | Address used for `ADMINS`, `DEFAULT_FROM_EMAIL` and the API contact (default `admin@example.com`). |
| `--ref REF` | Download a branch, tag or commit instead of the matching release, e.g. `--ref main`. |
| `--source PATH` | Copy a local django-starter checkout instead of downloading. `.git`, `node_modules`, `.venv`, `.env`, `db.sqlite3` and build output are left out. |
| `--no-install` | Skip `make init`; the manual setup steps are printed instead. |
| `--no-git` | Skip `git init`. |
| `--dir PATH` | Parent directory to create the project in (default: the current directory). |

The target directory must not exist or must be empty. If `make`, `uv` or (for the full variant) `npm`
is not installed, the generator skips `make init` and prints the equivalent steps:
`uv sync`, `npm install && npm run build` (full only) and `uv run python manage.py migrate`.

## Variants

Both variants share the same core: Django 6.1 on Python 3.14, a custom user model, `django-allauth`
with headless mode, Django REST Framework with a `drf-spectacular` OpenAPI schema, Django's built-in
tasks framework, SQLite for local development and a Docker Compose stack (Postgres + Redis + gunicorn)
for production.

**Full (default)** adds the server-rendered web app: Django templates, HTMX and Alpine.js for
interactivity, Tailwind CSS 4 built with the Tailwind CLI (no JavaScript bundler), allauth's account
pages, a profile page, sitemaps and meta tags.

**API-only (`--api`)** has no templates (other than the allauth email templates), no front-end assets
and no npm. allauth runs with `HEADLESS_ONLY = True`, so authentication is a JSON API meant for a
separate front end or mobile app.

## Authentication API

allauth headless serves its auth API under `/_allauth/`. Mobile and other non-browser clients use the
`app` client, which authenticates with a session token instead of cookies:

| Endpoint | Purpose |
| --- | --- |
| `POST /_allauth/app/v1/auth/signup` | Create an account. |
| `POST /_allauth/app/v1/auth/login` | Log in with email and password. |
| `GET /_allauth/app/v1/auth/session` | Check the current session. |
| `DELETE /_allauth/app/v1/auth/session` | Log out. |

A successful signup or login returns `meta.session_token`. Send it as the `X-Session-Token` header on
later requests, both to the allauth endpoints and to your own API views:

```bash
curl -s -X POST http://localhost:8000/_allauth/app/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com", "password": "..."}'

curl -s http://localhost:8000/api/users/me/ -H 'X-Session-Token: <session_token>'
```

`GET /api/users/me/` is the sample DRF endpoint: it returns the logged-in user. While `DEBUG` is on,
the full allauth API reference is served at <http://localhost:8000/_allauth/openapi.html>, and your
own DRF endpoints are documented at <http://localhost:8000/api/schema/swagger-ui/>.

Browser front ends can use the `browser` client (`/_allauth/browser/v1/...`), which uses Django's
session cookie and CSRF token. A browser SPA served from another origin (for example a Vite dev server
on port 5173) will also want [`django-cors-headers`](https://pypi.org/project/django-cors-headers/)
to allow its origin.

## License

MIT
