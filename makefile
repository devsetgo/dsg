# =============================================================================
# Project Variables
# =============================================================================
REPONAME = dsg
APP_VERSION = 2025-08-31-006

# Python Configuration
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest

# Path Configuration
SERVICE_PATH = src
TESTS_PATH = tests
LOG_PATH = log

# Server Configuration
DEV_SERVER = uvicorn ${SERVICE_PATH}.main:app
PROD_SERVER = uvicorn ${SERVICE_PATH}.main:app
PORT = 5000
WORKERS = 4
THREADS = 2

# Requirements and Environment
VENV_PATH = _venv
REQUIREMENTS_PATH = requirements.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt

# Dynamic Variables
TIMESTAMP := $(shell date +'%y-%m-%d-%H%M')
LOG_LEVEL := $(shell grep LOGGING_LEVEL .env | cut -d '=' -f2 | tr '[:upper:]' '[:lower:]')

# =============================================================================
# Safety Checks
# =============================================================================
# Make will use bash instead of sh
SHELL := /bin/bash

# Make will exit on errors
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# Delete target files if the command fails
.DELETE_ON_ERROR:

# Warn if variables are undefined
MAKEFLAGS += --warn-undefined-variables

# Disable built-in implicit rules
.SUFFIXES:

# =============================================================================
# Phony Targets
# =============================================================================
.PHONY: help all dev-setup quick-test alembic-current alembic-downgrade alembic-history alembic-init alembic-migrate alembic-rev alembic-stamp autoflake black cache cleanup clear-pycache compile docker-all docker-build docker-login docker-push docker-run flake8 install install-dev install-test-deps isort kill pyright ruff run-dev run-gdev run-gprd run-grdev run-local run-plocal run-prd run-real run-stage run-test test tests clean-test test-file test-marker bump bump-beta format validate

# =============================================================================
# Default Target
# =============================================================================
.DEFAULT_GOAL := help

# =============================================================================
# Help Target
# =============================================================================
help:  ## Display this help message
	@echo ""
	@printf "\033[0;36m████████████████████████████████████████████████████████████████\033[0m\n"
	@printf "\033[0;36m█                      \033[1;37m$(REPONAME) Makefile\033[0;36m                       █\033[0m\n"
	@printf "\033[0;36m████████████████████████████████████████████████████████████████\033[0m\n"
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1;37mUsage:\033[0m\n  make \033[0;36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[0;36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Quick Start
all: install format test ## Run the complete development workflow
	@printf "\033[0;32m✅ Complete workflow finished successfully!\033[0m\n"

dev-setup: install install-dev ## Set up development environment
	@printf "\033[0;32m✅ Development environment set up successfully!\033[0m\n"

quick-test: format ## Run quick tests (no pre-commit hooks)
	@printf "\033[1;33m🧪 Running quick tests...\033[0m\n"
	$(PYTEST)
	@printf "\033[0;32m✅ Quick tests passed!\033[0m\n"

##@ Database Migration (Alembic) Commands

alembic-init: ## Initialize Alembic
	@printf "\033[1;33m🗃️ Initializing Alembic...\033[0m\n"
	alembic init alembic
	@printf "\033[0;32m✅ Alembic initialized successfully!\033[0m\n"

alembic-migrate: ## Migrate database using Alembic
	@printf "\033[1;33m🚀 Running database migration...\033[0m\n"
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	/home/mike/dsg/.venv/bin/python -m alembic upgrade head
	@printf "\033[0;32m✅ Database migration completed!\033[0m\n"

alembic-rev: ## Create a new revision file
	@printf "\033[1;33m📝 Creating new Alembic revision...\033[0m\n"
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	read -p "Enter revision name: " name; \
	/home/mike/dsg/.venv/bin/python -m alembic revision --autogenerate -m "$$name"
	@printf "\033[0;32m✅ Revision created successfully!\033[0m\n"

alembic-current: ## Show the current revision
	@printf "\033[1;33m📋 Showing current revision...\033[0m\n"
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	/home/mike/dsg/.venv/bin/python -m alembic current

alembic-history: ## Show migration history
	@printf "\033[1;33m📚 Showing migration history...\033[0m\n"
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	/home/mike/dsg/.venv/bin/python -m alembic history

alembic-stamp: ## Stamp the database with a specific revision
	@printf "\033[1;33m🏷️ Stamping database revision...\033[0m\n"
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	read -p "Enter revision ID: " rev; \
	/home/mike/dsg/.venv/bin/python -m alembic stamp "$$rev"
	@printf "\033[0;32m✅ Database stamped successfully!\033[0m\n"

alembic-downgrade: ## Downgrade database using Alembic
	@printf "\033[1;33m⬇️ Downgrading database...\033[0m\n"
	@read -p "Enter revision name: " name; \
	alembic downgrade $$name
	@printf "\033[0;32m✅ Database downgraded successfully!\033[0m\n"

##@ Code Quality and Formatting

autoflake:  ## Remove unused imports and variables
	@printf "\033[1;33m🧹 Removing unused imports and variables...\033[0m\n"
	autoflake --in-place --remove-all-unused-imports -r $(SERVICE_PATH)
	autoflake --in-place --remove-all-unused-imports -r $(TESTS_PATH)
	@printf "\033[0;32m✅ Autoflake completed!\033[0m\n"

black:  ## Format code using black
	@printf "\033[1;33m🖤 Formatting code with Black...\033[0m\n"
	black $(SERVICE_PATH)
	black $(TESTS_PATH)
	@printf "\033[0;32m✅ Black formatting completed!\033[0m\n"

isort:  ## Sort imports using isort
	@printf "\033[1;33m📚 Sorting imports with isort...\033[0m\n"
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)
	@printf "\033[0;32m✅ Import sorting completed!\033[0m\n"

ruff:  ## Run ruff linter and formatter
	@printf "\033[1;33m🦀 Linting and fixing with Ruff...\033[0m\n"
	ruff check --fix --exit-non-zero-on-fix --show-fixes $(SERVICE_PATH) || true
	ruff check --fix --exit-non-zero-on-fix --show-fixes $(TESTS_PATH) || true
	@printf "\033[0;32m✅ Ruff linting completed!\033[0m\n"

format: isort ruff autoflake black ## Run all code formatting tools in the correct order
	@printf "\033[0;32m✅ All formatting tools completed!\033[0m\n"

cleanup: format ## Run all code formatting tools (alias for format)
	@printf "\033[0;32m✅ Code cleanup completed!\033[0m\n"

validate: ## Validate code without making changes
	@printf "\033[1;33m🔍 Validating code style...\033[0m\n"
	black --check $(SERVICE_PATH) $(TESTS_PATH)
	isort --check-only $(SERVICE_PATH) $(TESTS_PATH)
	ruff check $(SERVICE_PATH) $(TESTS_PATH)
	@printf "\033[0;32m✅ Code validation passed!\033[0m\n"

flake8:  ## Run flake8 and output report
	@printf "\033[1;33m📋 Running flake8 checks...\033[0m\n"
	flake8 --tee . > _flake8Report.txt
	@printf "\033[0;32m✅ Flake8 completed!\033[0m\n"

pyright:  ## Run pyright
	@printf "\033[1;33m🔍 Running pyright type checking...\033[0m\n"
	pyright
	@printf "\033[0;32m✅ Pyright completed!\033[0m\n"

##@ Cache and Cleanup

cache:  ## Clean pycache
	@printf "\033[1;33m🧹 Cleaning cache files...\033[0m\n"
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '.pytest_cache' -exec rm -rf {} +
	@printf "\033[0;32m✅ Cache cleanup completed!\033[0m\n"

clear-pycache: ## Clear pycache
	@printf "\033[1;33m🧹 Clearing pycache...\033[0m\n"
	find . -name '__pycache__' -exec rm -rf {} +
	@printf "\033[0;32m✅ Pycache cleared!\033[0m\n"

clean: ## Clean up generated files and caches
	@printf "\033[1;33m🧹 Cleaning up...\033[0m\n"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .ruff_cache/ 2>/dev/null || true
	@printf "\033[0;32m✅ Cleanup completed!\033[0m\n"

##@ Utilities

compile:  ## Compile http_request.c into a shared library
	@printf "\033[1;33m🔧 Compiling shared library...\033[0m\n"
	gcc -shared -o http_request.so http_request.c -lcurl -fPIC
	@printf "\033[0;32m✅ Compilation completed!\033[0m\n"

kill:  ## Kill any process running on the app port
	@printf "\033[1;33m🔪 Stopping processes on port ${PORT}...\033[0m\n"
	@echo "Stopping any process running on port ${PORT}..."
	@lsof -ti:${PORT} | xargs -r kill -9 || echo "No process found running on port ${PORT}"
	@echo "Port ${PORT} is now free"
	@printf "\033[0;32m✅ Port cleared!\033[0m\n"

##@ Docker Commands

docker-login:  ## Login to docker hub
	@printf "\033[1;33m🐳 Logging into Docker Hub...\033[0m\n"
	docker login
	@printf "\033[0;32m✅ Docker login completed!\033[0m\n"

docker-run:  ## Run docker container
	@printf "\033[1;33m🚀 Running Docker container...\033[0m\n"
	docker run -p 5000:5000 dsg:$(APP_VERSION)

docker-build:  ## Build docker image
	@printf "\033[1;33m🏗️ Building Docker image...\033[0m\n"
	docker build --no-cache -t dsg:$(APP_VERSION) .
	@printf "\033[0;32m✅ Docker image built successfully!\033[0m\n"

docker-push:  ## Push image to docker hub
	@printf "\033[1;33m⬆️ Pushing image to Docker Hub...\033[0m\n"
	docker tag dsg:$(APP_VERSION) mikeryan56/dsg:$(APP_VERSION)
	docker push mikeryan56/dsg:$(APP_VERSION)
	@printf "\033[0;32m✅ Image pushed successfully!\033[0m\n"

docker-all: docker-build docker-push ## Build and push Docker image
	@printf "\033[0;32m✅ Docker build and push completed!\033[0m\n"

##@ Setup and Installation

install:  ## Install required dependencies
	@printf "\033[1;33m📦 Installing dependencies...\033[0m\n"
	$(PIP) install -r $(REQUIREMENTS_PATH)
	@printf "\033[0;32m✅ Dependencies installed successfully!\033[0m\n"

install-dev:  ## Install development dependencies
	@printf "\033[1;33m📦 Installing development dependencies...\033[0m\n"
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)
	@printf "\033[0;32m✅ Development dependencies installed!\033[0m\n"

install-test-deps: ## Install test dependencies
	@printf "\033[1;33m📦 Installing test dependencies...\033[0m\n"
	pip install pytest pytest-cov pytest-asyncio pytest-mock httpx
	@printf "\033[0;32m✅ Test dependencies installed!\033[0m\n"

##@ Version Management

bump-beta:  ## Bump the beta version number using bumpcalver
	@printf "\033[1;33m📈 Bumping beta version...\033[0m\n"
	bumpcalver --build --beta
	@printf "\033[0;32m✅ Beta version bumped successfully!\033[0m\n"

bump:  ## Bump the version number using bumpcalver
	@printf "\033[1;33m📈 Bumping version...\033[0m\n"
	bumpcalver --build --git-tag
	@printf "\033[0;32m✅ Version bumped successfully!\033[0m\n"

##@ Application Server Commands

run-dev:  ## Run the FastAPI application in development mode with hot-reloading
	@printf "\033[1;33m🚀 Starting FastAPI in development mode...\033[0m\n"
	cp env-files/.env.dev .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-local:  ## Run the FastAPI application in local mode with hot-reloading
	@printf "\033[1;33m🏠 Starting FastAPI in local mode...\033[0m\n"
	cp env-files/.env.local .env
	@echo "Do you want to delete the SQLite database at /workspaces/dsg/sqlite_db/dsg_local.db? (y/N): " && read ans && [ "$$ans" = "y" ] && rm -f /workspaces/dsg/sqlite_db/dsg_local.db || echo "Database not deleted."
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-plocal:  ## Run the FastAPI application with plocal environment
	@printf "\033[1;33m🏠 Starting FastAPI with plocal environment...\033[0m\n"
	cp env-files/.env.plocal .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-test:  ## Run the FastAPI application in test mode
	@printf "\033[1;33m🧪 Starting FastAPI in test mode...\033[0m\n"
	cp env-files/.env.test .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-stage:  ## Run the FastAPI application in staging mode
	@printf "\033[1;33m🎭 Starting FastAPI in staging mode...\033[0m\n"
	cp env-files/.env.stage .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}

run-real:  ## Run the FastAPI application in real mode with workers
	@printf "\033[1;33m🌍 Starting FastAPI in real mode...\033[0m\n"
	cp env-files/.env.real .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}

run-prd:  ## Run the FastAPI application in production mode
	@printf "\033[1;33m🏭 Starting FastAPI in production mode...\033[0m\n"
	cp env-files/.env.server .env
	uvicorn ${SERVICE_PATH}.main:app --port 5000 --workers 1 --log-level debug

run-gdev:  ## Run the FastAPI application in development mode with granian
	@printf "\033[1;33m⚡ Starting FastAPI with Granian (dev mode)...\033[0m\n"
	cp env-files/.env.dev .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-gprd:  ## Run the FastAPI application in production mode with granian
	@printf "\033[1;33m⚡ Starting FastAPI with Granian (production)...\033[0m\n"
	cp env-files/.env.dev .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --workers 8 --log-level ${LOG_LEVEL}

run-grdev:  # Run the FastAPI application in development mode with granian and rsgi interface
	cp env-files/.env.dev .env
	granian --interface rsgi ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

##@ Testing and Quality Assurance

test: ## Run the project's tests
	@printf "\033[1;33m🧪 Running full test suite...\033[0m\n"
	pre-commit run -a
	pytest
	sed -i 's|<source>.*</source>|<source>$(REPONAME)</source>|' coverage.xml
	genbadge coverage -i coverage.xml
	genbadge tests -i report.xml
	@printf "\033[0;32m✅ All tests passed!\033[0m\n"

tests: test ## Run the project's tests

clean-test: ## Clean test artifacts
	@printf "\033[1;33m🧹 Cleaning test artifacts...\033[0m\n"
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage
	@printf "\033[0;32m✅ Test cleanup completed!\033[0m\n"

test-file: ## Run a specific test file
	@printf "\033[1;33m🧪 Running specific test file: $(FILE)...\033[0m\n"
	pytest tests/$(FILE) -v

test-marker: ## Run tests with specific marker
	@printf "\033[1;33m🧪 Running tests with marker: $(MARKER)...\033[0m\n"
	pytest tests/ -m $(MARKER) -v
