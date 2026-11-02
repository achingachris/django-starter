---
name: django
description: House conventions for writing code in this Django project (django-starter): ruff formatting and linting compliance, imports at module top with real refactors for circular imports, docstrings over comment blocks, maintained libraries over hand-rolled code, new code arrives with its tests, permission gating through has_perm, secrets in env vars and encrypted at rest, templates with no inline style blocks, allauth-based email templates, and the native-dev / Docker-prod split. Use this whenever writing, editing, or reviewing Python, templates, tests, settings, or deployment config in this project, even when the request is just "add a view" or "fix this bug" and says nothing about style. AGENTS.md takes precedence where they differ.
---

# Django conventions for django-starter

House rules for this project. Where `AGENTS.md` speaks, it wins; these conventions
fill in the practices it does not spell out, with the portable principle first and
this project's concrete values second.

## Conventions

### Code style: match ruff, and emit code that already passes

**Principle.** Whatever formatters and linters a project runs, match them and emit
code that passes them on the first try. Hand-formatting around a formatter wastes a
review cycle and produces a diff the next format run will undo.

**This project.** The stack is **ruff only** (format + lint), configured in
`pyproject.toml [tool.ruff]`: line length 120, double quotes, rules `E, F, I, UP, B,
SIM`, migrations excluded.

```bash
make ruff          # format + lint with autofix (ruff-format then ruff-lint)
make ruff-format   # ruff format .
make ruff-lint     # ruff check --fix .
make type-check    # mypy (django-stubs + drf-stubs); advisory, not a merge gate
```

Import sorting is ruff's isort rules (`I`), so there is no separate isort config and
no profile mismatch to worry about. There is no djlint: Django templates are indented
with two spaces and follow the template guidelines in `AGENTS.md`.

### Imports go at the top of the module

**Principle.** Every import belongs in the module's import block. An import buried
inside a function hides the module's real dependency graph, and it is almost always
there to paper over a circular import.

When an import is circular, **refactor it**. Do not move it inline and move on.
Django's escape hatches, roughly in order of how often they are the right answer:

- **String model references**: `ForeignKey("otherapp.Model")` never imports anything.
- **`django.apps.apps.get_model()`** inside code that runs after the app registry is
  ready (migrations, management commands).
- **Extract the shared piece.** If A and B both need something, it belongs in C.
- **`TYPE_CHECKING` guards** for annotation-only imports.
- **`AppConfig.ready()`** for signal registration, the most common cycle source.

Two inline imports are accepted: the guard inside `manage.py`, and an optional or
heavy dependency behind a feature check. Test files follow the same rule.

### Docstrings, not a stack of hash comments

**Principle.** What a function, method, or class does goes in a triple-quoted
docstring as its first statement — reachable from `help()`, `__doc__`, and IDE
tooltips, where hash comments are reachable from nowhere.

- Single line: `"""Short summary."""`; multi-line: summary, blank line, details.
- `#` comments explain a line or short block **inside** a body, nothing more.
- An `__init__.py` that "should be empty" gets a one-line module docstring instead.
- Upgrade hash-style function docs while editing nearby code; do not sweep the repo
  for them as a standalone change.

### Reach for a maintained library before writing your own

**Principle.** Before implementing a pattern by hand, spend two minutes checking PyPI
or awesome-django for a maintained package (a release within roughly two years,
supporting the Django version in use). Dependencies are cheap; custom code compounds.

**This project.** Add packages with `make uv add '<package>'`. The codebase already
leans this way: django-allauth, django-htmx, django-allauth's social providers.
When the ecosystem is abandoned or every option is
awkward, say so openly and explain the trade-off; rolling custom code silently is not
allowed.

### Tests: new code arrives with its tests

**Principle.** Writing the test is part of writing the change, not a follow-up. A new
branch, view, or model method gets a test that exercises it in the same commit.

**This project.** The Django test runner, not pytest. Tests live in
`apps/<app>/tests/`.

```bash
make test                                       # full suite
make test ARGS='apps.module.tests.test_file'    # one module
make test ARGS='path.to.test --keepdb'          # reuse the test DB for speed
```

There is no enforced coverage threshold; do not treat that as licence to skip tests,
and never add a threshold-lowering flag to make a change pass.

### Permissions: gate on `has_perm`, never on group membership

**Principle.** Every "is this user allowed to do this" check goes through Django
permissions: `user.has_perm("app.codename")` in Python, `{% if perms.app.codename %}`
in templates — never `user.groups.filter(name=...).exists()`. Groups are the grant
vehicle only; `has_perm` is how access is read.

- Gate the **action** and the **UI that offers it** with the same predicate. A hidden
  button is not access control, and a visible button that 403s is a bug.
- Object-level access is a data-model check and is fine: a helper testing
  `obj.owner_id` or membership in the data, not a group name.
- Keep read predicates free of side effects; anything that spends a credit or quota
  happens in a separate atomic call at write time.

**This project.** Auth is django-allauth and views currently gate on login state;
when role-based access emerges, build it on `has_perm` with thin named wrappers in a
`permissions.py`. The user model is `apps.users.models.CustomUser` (import it
directly), and models extend `apps.utils.models.BaseModel`.

### Secrets live in env vars, and secret fields are encrypted from the first commit

**Principle.** A model field holding a secret (OAuth token, API key, credential) uses
an encrypted field class in the same commit that introduces it. "Plaintext for now,
encrypt later" creates the rows that leak.

**This project.** Configuration secrets come from env vars via django-environ:
`.env` locally, `.env.prod` for the Docker stack. **Never overwrite `.env` without
asking first** (see `AGENTS.md`). There is no encrypted field class yet; when the
first secret-holding field arrives, adopt a maintained encrypted-field library in
that same commit rather than hand-rolling one. When work produces a secret the human
has to keep, point them at a password manager, not a wiki, notes app, or repo file.

### Templates and frontend

`AGENTS.md` owns the template and frontend rules (two-space indent, plain Tailwind
utilities, HTMX for server-backed interactions, Alpine.js for browser-only,
components via `{% include %}`, CSS compiled by the Tailwind CLI and loaded with
`{% static %}`). The one rule worth restating because it is easy to violate
casually: **no inline `<style>` blocks in templates** — styling comes from Tailwind
utilities (plus the few component classes in `assets/styles/app/tailwind/`), and anything
genuinely custom goes in `assets/styles/`.

### Running commands and finishing a change

**Principle.** Use the project's real entry points, keep the local loop fast, and
leave the commit to the human.

- Run tools through `uv run <cmd>` or the make targets; never
  `source .venv/bin/activate`.
- **Run `make test` after changing code.** Run `make ruff` when preparing work for
  review, not as a constant sanity pass.
- **Stage, do not commit.** `git add` the specific files and describe what is staged;
  no `git commit`, `git push`, or PR creation unless explicitly asked. Offering a
  commit message to copy is welcome.

### Email

**This project.** Dev uses the console backend (mail prints to the terminal); prod
sends SMTP via Resend (`RESEND_API_KEY` plus a `DEFAULT_FROM_EMAIL` on a verified
domain), configured in `config/settings/base.py`. Account email templates are
allauth overrides in `templates/account/email/` — follow that shape. If custom
transactional email is built later, write each body once (single source for the
plain-text and HTML parts) rather than maintaining parallel `.txt`/`.html` templates
that drift.

### Deployment: native dev, Docker prod

**Principle.** Everything host-specific stays in one seam, so moving hosts is a
config change rather than a rewrite.

**This project.** Local development runs natively (uv + SQLite + DummyCache + Django's
immediate task backend — no services needed). Production is the Docker Compose stack: gunicorn
web, Postgres, Redis, `config.settings.prod`, secrets from `.env.prod`,
static files served by whitenoise. The seam is `docker-compose.yml` + `.env.prod`.
See `README.md` and `AGENTS.md → Local vs production` before touching the
Dockerfile, compose file, or settings modules.
