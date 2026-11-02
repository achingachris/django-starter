include custom.mk

# Local development runs natively on your Python environment (uv) against SQLite.
# Docker is reserved for the production / full-stack containerized setup (see the `prod-*` targets).

# Set the user and group IDs used by the production docker compose so new files belong to the host
# user instead of root. These defaults are fine for most people.
export MY_UID := 1000
export MY_GID := 1000

setup-env:
	@[ ! -f ./.env ] && cp ./.env.example ./.env || echo ".env file already exists."

# -----------------------------------------------------------------------------
# Local development (native, uv + SQLite)
# -----------------------------------------------------------------------------

init: setup-env ## Quickly get up and running (install deps and bootstrap the SQLite DB)
	@echo "Installing Python dependencies"
	@uv sync
# >>> web
	@echo "Installing front-end dependencies and building the CSS"
	@npm install
	@npm run build
# <<< web
	@$(MAKE) migrate
	@echo ""
	@echo "✅ Project setup complete!"
	@echo "   Run 'make start' to launch the Django dev server at http://localhost:8000/"
# >>> web
	@echo "   Run 'make npm-dev' in a second terminal to rebuild the CSS as you edit templates."
# <<< web

start: ## Run the Django development server
	@uv run python manage.py runserver

shell: ## Get a Django shell
	@uv run python manage.py shell

dbshell: ## Get a database shell (SQLite locally)
	@uv run python manage.py dbshell

manage: ## Run any manage.py command. E.g. `make manage ARGS='createsuperuser'`
	@uv run python manage.py ${ARGS}

migrations: ## Create DB migrations
	@uv run python manage.py makemigrations

migrate: ## Run DB migrations
	@uv run python manage.py migrate

test: ## Run Django tests (uses config/settings/test.py)
	@uv run python manage.py test --settings=config.settings.test ${ARGS}

# -----------------------------------------------------------------------------
# Python tooling
# -----------------------------------------------------------------------------

uv: ## Run a uv command
	@uv $(filter-out $@,$(MAKECMDGOALS))

requirements: ## Sync Python dependencies from the lockfile
	@uv sync --frozen

ruff-format: ## Runs ruff formatter on the codebase
	@uv run ruff format .

ruff-lint:  ## Runs ruff linter on the codebase
	@uv run ruff check --fix .

ruff: ruff-format ruff-lint ## Formatting and linting using Ruff

type-check: ## Run Python type checking
	@uv run mypy .

# >>> web
# -----------------------------------------------------------------------------
# Front end (native npm)
# -----------------------------------------------------------------------------

npm-install-all: ## Runs npm install
	@npm install

npm-install: ## Runs npm install (optionally accepting package names)
	@npm install $(filter-out $@,$(MAKECMDGOALS))

npm-uninstall: ## Runs npm uninstall (takes package name(s))
	@npm uninstall $(filter-out $@,$(MAKECMDGOALS))

npm-build: ## Build the CSS and copy vendored JS/fonts into static/ (production assets)
	@npm run build

npm-dev: ## Rebuild the CSS whenever templates change (optional second terminal)
	@npm run dev

upgrade: requirements migrations migrate npm-install npm-build  ## Update requirements, migrate the database, and rebuild the front end
# <<< web
# api-only: upgrade: requirements migrations migrate  ## Update requirements and migrate the database

# -----------------------------------------------------------------------------
# Production (Docker / docker compose)
# -----------------------------------------------------------------------------
# The stack (gunicorn web + Postgres + Redis) reads secrets from .env.prod
# and runs with DJANGO_SETTINGS_MODULE=config.settings.prod.

setup-env-prod: ## Create .env.prod from the template if it doesn't exist
	@[ ! -f ./.env.prod ] && cp ./.env.prod.example ./.env.prod && \
		echo "✅ Created .env.prod — fill in real secrets before deploying." || \
		echo ".env.prod file already exists."

prod-build: setup-env-prod ## Build the production docker images
	@docker compose build

prod-start: setup-env-prod ## Start the production docker containers
	@docker compose up

prod-start-bg: setup-env-prod ## Start the production docker containers in the background
	@docker compose up -d

prod-stop: ## Stop the production docker containers
	@docker compose down

prod-restart: prod-stop prod-start ## Restart the production docker containers

prod-ssh: ## SSH into the running production web container
	@docker compose exec web bash

prod-manage: ## Run a manage.py command in the production web container. E.g. `make prod-manage ARGS='migrate'`
	@docker compose run --rm web python manage.py ${ARGS}

.PHONY: help
.DEFAULT_GOAL := help

help:
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# catch-all for any undefined targets - this prevents error messages
# when running things like make npm-install <package>
%:
	@:
