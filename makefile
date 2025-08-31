# Shell
SHELL := /bin/bash
# Variables
__version__ = 2025-08-30-002
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest

SERVICE_PATH = src
TESTS_PATH = tests
LOG_PATH = log

DEV_SERVER = uvicorn ${SERVICE_PATH}.main:app
PROD_SERVER = uvicorn ${SERVICE_PATH}.main:app
PORT = 5000
WORKERS = 4
THREADS = 2

VENV_PATH = _venv
REQUIREMENTS_PATH = requirements.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt

TIMESTAMP := $(shell date +'%y-%m-%d-%H%M')
LOG_LEVEL := $(shell grep LOGGING_LEVEL .env | cut -d '=' -f2 | tr '[:upper:]' '[:lower:]')

.PHONY: alembic-downgrade alembic-init alembic-migrate alembic-rev autoflake black cache cleanup compile dev docker-beta-bp docker-beta-build docker-beta-push docker-beta-run flake8 gdev gprd grdev help install install-dev isort kill prd run-dev run-gdev run-gprd run-grdev run-local run-prod run-real run-test test bump bump-beta bump-rc bump-release bump-custom bump-git bump-beta-git

alembic-init: # Initialize Alembic
	alembic init alembic

alembic-migrate: # Migrate database using Alembic
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	/home/mike/dsg/.venv/bin/python -m alembic upgrade head

alembic-rev: # Create a new revision file
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	read -p "Enter revision name: " name; \
	/home/mike/dsg/.venv/bin/python -m alembic revision --autogenerate -m "$$name"

alembic-current: # Show the current revision
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	/home/mike/dsg/.venv/bin/python -m alembic current

alembic-history: # Show migration history
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	/home/mike/dsg/.venv/bin/python -m alembic history

alembic-stamp: # Stamp the database with a specific revision
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=$$(cat /tmp/db_url.txt) && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL" && \
	read -p "Enter revision ID: " rev; \
	/home/mike/dsg/.venv/bin/python -m alembic stamp "$$rev"


alembic-downgrade: # Downgrade database using Alembic
	@read -p "Enter revision name: " name; \
	alembic downgrade $$name

autoflake:  # Remove unused imports and variables
	autoflake --in-place --remove-all-unused-imports -r $(SERVICE_PATH)

black:  # Format code using black
	black $(SERVICE_PATH)
	black $(TESTS_PATH)

cache:  # Clean pycache
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '.pytest_cache' -exec rm -rf {} +

cleanup: autoflake ruff isort  # Run isort, ruff, and autoflake

clear-pycache: ## Clear pycache
	find . -name '__pycache__' -exec rm -rf {} +

compile:  # Compile http_request.c into a shared library
	gcc -shared -o http_request.so http_request.c -lcurl -fPIC

docker-login:  # Login to docker hub
	docker login

docker-run:  # Run docker container
	docker run -p 5000:5000 dsg:$(__version__)

docker-build:  # Build docker image
	docker build --no-cache -t dsg:$(__version__) .

docker-push:  # Push beta test image to docker hub
	docker tag dsg:$(__version__) mikeryan56/dsg:$(__version__)
	docker push mikeryan56/dsg:$(__version__)

docker-all: docker-build docker-push

bump-beta:  # Bump the beta version number using bumpcalver
	bumpcalver --build --beta

bump:  # Bump the version number using bumpcalver
	bumpcalver --build --git-tag


flake8:  # Run flake8 and output report
	flake8 --tee . > _flake8Report.txt

help:  # Display available targets
	@awk 'BEGIN {FS = ":  # "} /^[a-zA-Z_-]+:  # / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

kill:  # Kill any process running on the app port
	@echo "Stopping any process running on port ${PORT}..."
	@lsof -ti:${PORT} | xargs -r kill -9 || echo "No process found running on port ${PORT}"
	@echo "Port ${PORT} is now free"

install:  # Install required dependencies
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:  # Install development dependencies
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

isort:  # Sort imports using isort
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)

pyright:  # Run pyright
	pyright

run-dev:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.dev .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}
# uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}

run-local:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.local .env
	@echo "Do you want to delete the SQLite database at /workspaces/dsg/sqlite_db/dsg_local.db? (y/N): " && read ans && [ "$$ans" = "y" ] && rm -f /workspaces/dsg/sqlite_db/dsg_local.db || echo "Database not deleted."
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}


run-plocal:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.plocal .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-real:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.real .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}
# granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --threads ${THREADS} --http auto --log-level ${LOG_LEVEL}
# uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload


run-test:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.test .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-stage:  # Run the FastAPI application in production mode
	cp env-files/.env.stage .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL}

run-prd:  # Run the FastAPI application in production mode
	cp env-files/.env.server .env
	uvicorn ${SERVICE_PATH}.main:app --port 5000 --workers 1 --log-level debug

run-gdev:  # Run the FastAPI application in development mode with hot-reloading using granian
	cp env-files/.env.dev .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

run-gprd:  # Run the FastAPI application in production mode using granian
	cp env-files/.env.dev .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --workers 8 --log-level ${LOG_LEVEL}

run-grdev:  # Run the FastAPI application in development mode with hot-reloading using granian and rsgi interface
	cp env-files/.env.dev .env
	granian --interface rsgi ${SERVICE_PATH}.main:app --port ${PORT} --reload --log-level ${LOG_LEVEL}

# Install test dependencies
install-test-deps:
	pip install pytest pytest-cov pytest-asyncio pytest-mock httpx

# Testing commands
test: ## Run the project's tests
	pre-commit run -a
	pytest
	sed -i 's|<source>.*</source>|<source>$(REPONAME)</source>|' coverage.xml
	genbadge coverage -i coverage.xml
	genbadge tests -i report.xml
# flake8 src tests examples | tee htmlcov/_flake8Report.txt

tests: test ## Run the project's tests

# test:
# 	pytest tests/ -v

# test-cov:
# 	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# test-cov-threshold:
# 	pytest tests/ --cov=src --cov-fail-under=85

# test-fast:
# 	pytest tests/ -x --ff

# test-debug:
# 	pytest tests/ -v -s --pdb

clean-test:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage

# Run a specific test file
test-file:
	pytest tests/$(FILE) -v

# Run tests with specific marker
test-marker:
	pytest tests/ -m $(MARKER) -v

.PHONY: test test-cov test-cov-threshold test-fast test-debug clean-test install-test-deps test-file test-marker
