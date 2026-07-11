# Codebase Guidelines

## Architecture

- This is a Django project built on Python 3.14.
- User authentication uses `django-allauth`.
- The front end is mostly standard Django views and templates.
- HTMX and Alpine.js are used to provide single-page-app user experience with Django templates.
  HTMX is used for interactions which require accessing the backend, and Alpine.js is used for
  browser-only interactions.
- JavaScript files are kept in the `/assets/` folder and built by vite.
  JavaScript code is typically loaded via the static files framework inside Django templates using `django-vite`.
- APIs use Django Rest Framework, and JavaScript code that interacts with APIs uses an
  auto-generated OpenAPI-schema-baesd client.
- The front end uses Tailwind (Version 4) and DaisyUI.
- Celery is used for background jobs and scheduled tasks.

### Local vs production

The project runs in two modes, driven by `DEBUG` and a few env vars:

- **Local development** runs **natively** (no Docker) via `uv` + `npm` and uses **SQLite**,
  Django's `DummyCache`, and **eager (synchronous) Celery** — so no Postgres or Redis is required.
- **Production** uses the Docker Compose stack with **Postgres** (database), **Redis** (cache +
  Celery broker), and a dedicated Celery worker. Select `config.settings.prod` and set
  `DATABASE_URL` / `REDIS_URL` in the environment.

Settings live in the `config/settings/` package: `base.py` (shared), `dev.py` (default, local
development), and `prod.py` (production). `DJANGO_SETTINGS_MODULE` defaults to `config.settings.dev`.

See `README.md` for full setup details.

## Commands you can run

The following commands can be used for various tools and workflows.
A `Makefile` is provided to help centralize commands. Local-development targets run natively via
`uv`; production targets are prefixed with `prod-` and use Docker.

```bash
make  # List available commands
```

### First-time Setup

```bash
make init  # copy .env, uv sync, npm install, create + migrate the SQLite DB
```

### Starting the Application

Local development needs **two processes in two terminals** (in DEBUG, assets are served by Vite):

```bash
make start     # Terminal 1: Django dev server (http://localhost:8000)
make npm-dev   # Terminal 2: Vite front-end dev server (port 5173)
```

To run the production containerized stack instead (Postgres + Redis + gunicorn web + Celery),
configure `.env.prod` first (`make setup-env-prod`), then:

```bash
make prod-build      # build the production image
make prod-start      # foreground
make prod-start-bg   # background
make prod-stop       # stop the containers
```

## Common Commands

### Development

```bash
make shell            # Open Python / Django shell
make dbshell          # Open a database shell (SQLite locally)
make manage ARGS='command'  # Run any Django management command
make prod-ssh         # Shell into the running production web container (Docker)
```

### Database

```bash
make migrations       # Create new migrations
make migrate          # Apply migrations
```

### Testing

```bash
make test                              # Run all tests
make test ARGS='apps.module.tests.test_file'  # Run specific test
make test ARGS='path.to.test --keepdb'        # Run with options
```

### Python Code Quality

```bash
make ruff-format      # Format code
make ruff-lint        # Lint and auto-fix
make ruff             # Run both format and lint
```
### Python

```bash
make uv add '<package>'         # Add a new package
make requirements               # Sync Python dependencies from the lockfile (uv sync --frozen)
make uv run '<command> <args>'  # Run a Python command
```

### Frontend

```bash
make npm-install      # Install npm packages
make npm-install package-name  # Install specific package
make npm-uninstall package-name  # Uninstall package
make npm-dev          # Run the Vite development server
make npm-build        # Build for production
make npm-type-check   # Run TypeScript type checking
```

Note: In local development, run `make npm-dev` in a second terminal alongside `make start` — the
Vite dev server provides hot-reloaded CSS/JS. Without it, pages load unstyled.

### Code generation

```bash
make uv run 'pegasus startapp <app_name> <Model1> <Model2Name>'  # Start a new Django app (models are optional)
```

## General Coding Preferences

- Always prefer simple solutions.
- Avoid duplication of code whenever possible, which means checking for other areas of the codebase that might already have similar code and functionality.
- You are careful to only make changes that are requested or you are confident are well understood and related to the change being requested.
- When fixing an issue or bug, do not introduce a new pattern or technology without first exhausting all options for the existing implementation. And if you finally do this, make sure to remove the old implementation afterwards so we don’t have duplicate logic.
- Keep the codebase clean and organized.
- Avoid writing scripts in files if possible, especially if the script is likely only to be run once.
- Try to avoid having files over 200-300 lines of code. Refactor at that point.
- Don't ever add mock data to functions. Only add mocks to tests or utilities that are only used by tests.
- Always think about what other areas of code might be affected by any changes made.
- Never overwrite my .env file without first asking and confirming.

## Python Code Guidelines

### Code Style

- Follow PEP 8 with 120 character line limit.
- Use double quotes for Python strings (ruff enforced).
- Sort imports with isort (via ruff).
- Try to use type hints in new code. However, strict type-checking is not enforced and you can leave them out if it's burdensome.
  There is no need to add type hints to existing code if it does not already use them.

### Python 3.14 syntax notes

- **Unparenthesized `except` with multiple exception types is valid** (PEP 758, Python 3.14+).
  `except ValueError, TypeError:` is equivalent to `except (ValueError, TypeError):` — it is **not**
  Python 2 syntax and will **not** raise a `SyntaxError`. Parentheses are still required when using
  `as` (e.g. `except (ValueError, TypeError) as e:`). Do not "fix" unparenthesized forms unless an
  `as` clause is being added.

### Preferred Practices

- Use Django signals sparingly and document them well.
- Always use the Django ORM if possible. Use best practices like lazily evaluating querysets
  and selecting or prefetching related objects when necessary.
- Use function-based views by default, unless using a framework that relies on class-based views (e.g. Django Rest Framework).
- Always validate user input server-side.
- Handle errors explicitly, avoid silent failures.

#### Django models

- All Django models should extend `apps.utils.models.BaseModel` (which adds `created_at` and `updated_at` fields).
- The project's user model is `apps.users.models.CustomUser` and should be imported directly.

## Django Template Coding Guidelines for HTML files

- Indent templates with two spaces.
- Use standard Django template syntax.
- For multi-line comments, use `{% comment %}...{% endcomment %}`. The `{# ... #}` syntax is single-line only and does NOT work across multiple lines — never write `{# first line\n   second line #}`.
- JavaScript and CSS files built with vite should be included with the `{% vite_asset %}` template tag provided by `django-vite` (must have `{% load django_vite %}` at the top of the template)
- Any react components also need `{% vite_react_refresh %}` for Vite + React's HMR functionality, from the same `django_vite` template library)
- Use the Django `{% static %}` tag for loading images and external JavaScript / CSS files not managed by vite.
- Prefer using alpine.js for page-level JavaScript, and avoid inline `<script>` tags where possible.
- Break re-usable template components into separate templates with `{% include %}` statements.
  These normally go into a `components` folder.
- Use DaisyUI styling markup for available components. When not available, fall back to standard TailwindCSS classes.
- Stick with the DaisyUI color palette whenever possible.

## JavaScript Code Guidelines

### Code Style

- Use ES6+ syntax for JavaScript code.
- Use 2 spaces for indentation in JavaScript, JSX, and HTML files.
- Use single quotes for JavaScript strings.
- End statements with semicolons.
- Use camelCase for variable and function names.
- Use PascalCase for component names (React).
- Use explicit type annotations in TypeScript files.
- Use ES6 import/export syntax for module management.

### Preferred Practices
- When using HTMX, follow progressive enhancement patterns.
- Use Alpine.js for client-side interactivity that doesn't require server interaction.
- Avoid inline `<script>` tags wherever posisble.
- Validate user input on both client and server side.
- Handle errors explicitly in promise chains and async functions.

### Build System

- Code is bundled using vite and served with `django-vite`.
