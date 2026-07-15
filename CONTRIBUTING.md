# Contributing

Thanks for your interest in contributing to this project! This document explains how to set up
your environment, the standards we follow, and how to submit issues and pull requests.

## Table of contents

- [Getting started](#getting-started)
- [Reporting issues](#reporting-issues)
- [Suggesting features](#suggesting-features)
- [Submitting pull requests](#submitting-pull-requests)
- [Code style](#code-style)
- [Running tests](#running-tests)
- [Project conventions](#project-conventions)

## Getting started

Local development runs **natively** (no Docker) using [uv](https://docs.astral.sh/uv/) and `npm`
against SQLite. See the [README](README.md) for full details.

### Prerequisites

- **Python 3.14** with a virtual environment tool of your choice.
  [uv](https://docs.astral.sh/uv/getting-started/installation/) is recommended (the `Makefile`
  targets use it, and it provisions Python 3.14 for you), but it is not a must — `venv` + `pip`,
  virtualenv, Poetry, etc. all work. Dependencies are declared in `pyproject.toml`.
- [Node.js](https://nodejs.org/) 20+ — provides `node` and `npm`
- `make` — preinstalled on macOS/Linux

### Setup

With uv (recommended — matches the `Makefile` and CI):

```bash
make init      # copy .env, install Python + npm dependencies, create and migrate the SQLite DB
```

With another environment tool, the equivalent steps are:

```bash
cp .env.example .env
python3.14 -m venv .venv && source .venv/bin/activate   # or your preferred tool
pip install -e .            # runtime dependencies (from pyproject.toml)
pip install --group dev     # dev tools: pre-commit, ruff, mypy, etc. (needs pip 25.1+)
npm install
python manage.py migrate
```

The rest of this guide shows `make` / `uv run` commands; if you're not using uv, run the
underlying command directly inside your activated environment (e.g. `python manage.py test`
instead of `make test`).

Then run the app with **two processes in two terminals**:

```bash
make start     # Terminal 1: Django dev server (http://localhost:8000)
make npm-dev   # Terminal 2: Vite front-end dev server (hot-reloaded CSS/JS)
```

Run `make` with no arguments to list all available commands.

## Reporting issues

Before opening an issue, please search
[existing issues](../../issues) to avoid duplicates.

When filing a bug report, use the **Bug report** issue template and include:

- Clear steps to reproduce the problem
- What you expected to happen vs. what actually happened
- Your environment (OS, Python/Node versions, local vs. Docker production mode)
- Relevant logs, tracebacks, or screenshots

## Suggesting features

Use the **Feature request** issue template. Describe the problem you're trying to solve, not just
the solution — this helps us evaluate alternatives. For large changes, please open an issue to
discuss the approach *before* investing time in a pull request.

## Submitting pull requests

1. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b my-feature main
   ```
2. Make your changes, keeping each pull request **focused on a single concern**.
3. Ensure the full local check suite passes (see below).
4. Write a clear PR description using the pull request template — explain **what** changed and
   **why**, and link any related issues (e.g. `Fixes #123`).
5. Be responsive to review feedback; maintainers may request changes before merging.

Every pull request must pass CI, which runs:

| Check | Command to reproduce locally |
|-------|------------------------------|
| Code style (pre-commit: ruff + hygiene hooks) | `pre-commit run --all-files` |
| Type checking (mypy) | `mypy .` |
| Django tests (against Postgres + Redis in CI) | `make test` (or `python manage.py test`) |
| Front-end build + TypeScript check | `make npm-build && make npm-type-check` |

(Run these inside your activated environment; with uv, prefix Python commands with `uv run`.)

## Code style

- **Python**: PEP 8 with a 120-character line limit, double quotes, isort-sorted imports — all
  enforced by [ruff](https://docs.astral.sh/ruff/). Run `make ruff` to format and lint.
- **JavaScript/TypeScript**: ES6+, 2-space indentation, single quotes, semicolons.
- **Django templates**: 2-space indentation, DaisyUI/Tailwind classes for styling.
- Prefer simple solutions and avoid duplicating existing functionality.
- Use type hints in new Python code where practical.

We recommend installing the git hooks so style issues are caught before you push:

```bash
pre-commit install   # prefix with `uv run` if using uv
```

## Running tests

```bash
make test                                       # run all tests
make test ARGS='apps.module.tests.test_file'    # run a specific test module
make test ARGS='path.to.test --keepdb'          # pass extra options
```

New features and bug fixes should include tests covering the change.

## Project conventions

- Django models extend `apps.utils.models.BaseModel` (adds `created_at` / `updated_at`).
- The user model is `apps.users.models.CustomUser` — import it directly.
- Prefer function-based views, except where a framework expects class-based views (e.g. DRF).
- HTMX for server-backed interactivity, Alpine.js for browser-only interactivity.
- Front-end assets live in `/assets/` and are built by Vite; load them in templates with
  `{% vite_asset %}`.
- Use Django signals sparingly and document them well.
- Always validate user input server-side.
