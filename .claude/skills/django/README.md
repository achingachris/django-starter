# django

House conventions for writing code in this project. Adapted from
[Mariatta/claude-skills](https://github.com/Mariatta/claude-skills) with
django-starter's concrete values baked in; `AGENTS.md` takes precedence where
they differ.

- **Code style** — ruff only (format + lint, 120 cols, double quotes); emit code
  that already passes `make ruff`.
- **Imports** — everything at module top. Circular imports get refactored, not
  moved inline.
- **Docstrings** — triple-quoted first statement, not a stack of `#` comments.
- **Dependencies** — check for a maintained library before hand-rolling a pattern.
- **Tests** — new code arrives with its tests (`make test`, Django test runner).
- **Permissions** — gate on `has_perm`, never on group membership.
- **Secrets** — env vars via django-environ; secret model fields encrypted in the
  same commit they appear in.
- **Templates** — no inline `<style>` blocks; plain Tailwind per `AGENTS.md`.
- **Session workflow** — `uv run` / make targets, run tests after changes, stage
  but never commit unasked.
- **Email** — console backend in dev, Resend SMTP in prod, allauth templates.
- **Deployment** — native local dev, Docker Compose (gunicorn + Celery + Postgres
  + Redis) for production.
