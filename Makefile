include custom.mk

# Local development runs natively on your Python environment (uv) against SQLite.
# Docker is reserved for the production / full-stack containerized setup (see the `prod-*` targets).

# Set the user and group IDs used by the production docker compose so new files belong to the host
# user instead of root. These defaults are fine for most people.
export MY_UID := 1000
export MY_GID := 1000

# Pin the OpenAPI Generator version used to build the TypeScript API client (see `generate-api-client`).
# Keep this in sync with api-client/.openapi-generator/VERSION.
OPENAPI_GENERATOR_VERSION := 7.9.0

setup-env:
	@[ ! -f ./.env ] && cp ./.env.example ./.env || echo ".env file already exists."

# -----------------------------------------------------------------------------
# Local development (native, uv + SQLite)
# -----------------------------------------------------------------------------

init: setup-env ## Quickly get up and running (install deps and bootstrap the SQLite DB)
	@echo "Installing Python dependencies"
	@uv sync
	@echo "Installing front-end dependencies"
	@npm install
	@$(MAKE) migrate
	@echo ""
	@echo "✅ Project setup complete!"
	@echo "   Run 'make start' to launch the Django dev server at http://localhost:8000/"
	@echo "   Run 'make npm-dev' in a second terminal for the Vite front-end pipeline."

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

test: ## Run Django tests
	@uv run python manage.py test ${ARGS}

celery: ## Run a Celery worker with beat (requires a running Redis broker)
	@uv run celery -A chrisdevcode worker -l INFO --beat --pool=solo

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

# -----------------------------------------------------------------------------
# Front end (native npm)
# -----------------------------------------------------------------------------

npm-install-all: ## Runs npm install
	@npm install

npm-install: ## Runs npm install (optionally accepting package names)
	@npm install $(filter-out $@,$(MAKECMDGOALS))

npm-uninstall: ## Runs npm uninstall (takes package name(s))
	@npm uninstall $(filter-out $@,$(MAKECMDGOALS))

npm-build: ## Runs npm build (for production assets)
	@npm run build

npm-dev: ## Runs the Vite dev server
	@npm run dev

npm-type-check: ## Runs the type checker on the front end TypeScript code
	@npm run type-check

upgrade: requirements migrations migrate npm-install npm-dev  ## Run after a Pegasus upgrade to update requirements, migrate the database, and rebuild the front end

# -----------------------------------------------------------------------------
# API client code generation
# -----------------------------------------------------------------------------

generate-api-client: ## Regenerate the TypeScript API client (api-client/) from the OpenAPI schema
	@echo "Exporting OpenAPI schema from Django..."
	@uv run python manage.py spectacular --file schema.yaml --validate
	@echo "Pinning openapi-generator $(OPENAPI_GENERATOR_VERSION)..."
	@npx --yes @openapitools/openapi-generator-cli version-manager set $(OPENAPI_GENERATOR_VERSION) >/dev/null
	@echo "Generating TypeScript client into api-client/..."
	@npx --yes @openapitools/openapi-generator-cli generate \
		-i schema.yaml \
		-g typescript-fetch \
		-o api-client
	@rm -f schema.yaml
	@echo "✅ api-client regenerated. Review the diff before committing."

# -----------------------------------------------------------------------------
# Production (Docker / docker compose)
# -----------------------------------------------------------------------------

prod-build: ## Build the production docker images
	@docker compose build

prod-start: ## Start the production docker containers
	@docker compose up

prod-start-bg: ## Start the production docker containers in the background
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
