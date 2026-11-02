# Codebase Guidelines

## Architecture

- This is a Django project built on Python 3.14.
- User authentication uses `django-allauth`.
- The front end is mostly standard Django views and templates.
- HTMX and Alpine.js are used to provide single-page-app user experience with Django templates.
  HTMX is used for interactions which require accessing the backend, and Alpine.js is used for
  browser-only interactions.
- There is no JavaScript bundler. Site-wide JavaScript is a plain script at `static/javascript/site.js`;
  htmx, Alpine.js and Font Awesome are copied from `node_modules` into `static/vendor/` by `npm run build`.
- CSS is written in `assets/styles/site.css` and compiled by the Tailwind CLI into `static/css/site.css`.
- APIs use Django Rest Framework with an OpenAPI schema from `drf-spectacular`.
- The front end uses Tailwind (Version 4) with plain utility classes and no component library.
- The main database is Postgres.
- Background jobs use Django's built-in tasks framework (`django.tasks`) with the immediate backend.
- Redis is used as the default cache in production.

## Commands you can run

The following commands can be used for various tools and workflows.
A `Makefile` is provided to help centralize commands:

```bash
make  # List available commands
```

### First-time Setup

```bash
make init
```

### Starting the Application

```bash
make start     # Run in foreground with logs
make start-bg  # Run in background
```

Access the app at http://localhost:8000

### Stopping Services

```bash
make stop
```

## Common Commands

### Development

```bash
make ssh              # SSH into web container
make shell            # Open Python / Django shell
make dbshell          # Open PostgreSQL shell
make manage ARGS='command'  # Run any Django management command
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
make requirements               # Rebuild and restart containers after updating packages
make uv run '<command> <args>'  # Run a Python command
```

### Frontend

```bash
make npm-install      # Install npm packages
make npm-install package-name  # Install specific package
make npm-uninstall package-name  # Uninstall package
make npm-dev          # Rebuild the CSS whenever templates change (Tailwind CLI --watch)
make npm-build        # Build for production
```


### Creating a new app

```bash
mkdir apps/<app_name>
make manage ARGS='startapp <app_name> apps/<app_name>'
```

Then set `name = "apps.<app_name>"` in the generated `apps.py`, add `"apps.<app_name>"` to `INSTALLED_APPS`,
and extend `apps.utils.models.BaseModel` in its models.

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
- Load CSS, JavaScript and images with the Django `{% static %}` tag. The compiled stylesheet is `css/site.css`;
  vendored libraries live under `vendor/` and project scripts under `javascript/`, all inside `static/`.
- Prefer using alpine.js for page-level JavaScript, and avoid inline `<script>` tags where possible.
- Break re-usable template components into separate templates with `{% include %}` statements.
  These normally go into a `components` folder.
- Style with plain Tailwind utility classes and the default Tailwind palette (gray for neutrals, red/green/amber/blue for status).
- The only shared component classes are the button (`btn`, `btn-primary`, `btn-outline`, `btn-ghost`, `btn-danger`, `btn-xs`/`btn-sm`/`btn-lg`),
  form control (`form-input`, `form-checkbox`) and sidebar nav (`nav-title`, `nav-link`, `nav-link-active`) classes defined in
  `assets/styles/app/tailwind/app-components.css`. Do not add a component library; keep the CSS setup minimal.

## JavaScript Code Guidelines

### Code Style

- Use ES6+ syntax for JavaScript code.
- Use 2 spaces for indentation in JavaScript, JSX, and HTML files.
- Use single quotes for JavaScript strings.
- End statements with semicolons.
- Use camelCase for variable and function names.
- Use PascalCase for component names (React).
- There is no bundler: scripts are plain browser JavaScript wrapped in an IIFE, not ES modules.

### Preferred Practices
- When using HTMX, follow progressive enhancement patterns.
- Use Alpine.js for client-side interactivity that doesn't require server interaction.
- Avoid inline `<script>` tags wherever posisble.
- Validate user input on both client and server side.
- Handle errors explicitly in promise chains and async functions.

### Build System

- There is no JavaScript build. `npm run build` compiles the Tailwind CSS and copies vendored libraries into `static/`.
