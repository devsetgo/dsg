# Shell
SHELL := /bin/bash
# Variables
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

VENV_PATH = _venv
REQUIREMENTS_PATH = requirements.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt

.PHONY: alembic-downgrade alembic-init alembic-migrate alembic-rev autoflake black cache cleanup compile dev docker-beta-bp docker-beta-build docker-beta-push docker-beta-run flake8 gdev gprd grdev help install install-dev isort prd run-dev run-gdev run-gprd run-grdev run-local run-prod run-real run-test test

alembic-init: # Initialize Alembic
	alembic init alembic

alembic-migrate: # Migrate database using Alembic
	alembic upgrade head

alembic-rev: # Create a new revision file
	cp env-files/.env.test .env && \
	./scripts/env.sh && \
	export DATABASE_URL=`cat /tmp/db_url.txt` && \
	echo "In Makefile, DATABASE_URL is: $$DATABASE_URL"
	@read -p "Enter revision name: " name; \
	alembic revision --autogenerate -m "$$name"

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

compile:  # Compile http_request.c into a shared library
	gcc -shared -o http_request.so http_request.c -lcurl -fPIC

TIMESTAMP := $(shell date +'%y-%m-%d-%H%M')

docker-beta-run:  # Run docker container
	docker run -p 5000:5000 dsg:beta-$(TIMESTAMP)

docker-beta-build:  # Build docker image
	docker build --no-cache -t dsg:beta-$(TIMESTAMP) .

docker-beta-push:  # Push beta test image to docker hub
	docker tag dsg:beta-$(TIMESTAMP) mikeryan56/dsg:beta-$(TIMESTAMP)
	docker push mikeryan56/dsg:beta-$(TIMESTAMP)
	
docker-beta-bp: docker-beta-build docker-beta-push

file-process:
	cp

flake8:  # Run flake8 and output report
	flake8 --tee . > _flake8Report.txt

help:  # Display available targets
	@awk 'BEGIN {FS = ":  # "} /^[a-zA-Z_-]+:  # / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  # Install required dependencies
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:  # Install development dependencies
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

isort:  # Sort imports using isort
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)

run-dev:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.dev .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload


run-local:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.local .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload

run-plocal:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.plocal .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload


run-real:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.real .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload
	#uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS}
	


run-test:  # Run the FastAPI application in development mode with hot-reloading
	cp env-files/.env.test .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload

run-stage:  # Run the FastAPI application in production mode
	cp env-files/.env.stage .env
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS}

run-gdev:  # Run the FastAPI application in development mode with hot-reloading using granian
	cp env-files/.env.dev .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --reload

run-gprd:  # Run the FastAPI application in production mode using granian
	cp env-files/.env.prd .env
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS}

run-grdev:  # Run the FastAPI application in development mode with hot-reloading using granian and rsgi interface
	cp env-files/.env.dev .env
	granian --interface rsgi ${SERVICE_PATH}.main:app --port ${PORT} --reload


test:  # Run tests and generate coverage report
	pre-commit run -a
	PYTHONPATH=. pytest
	sed -i 's|<source>/workspaces/dsg</source>|<source>/github/workspace/dsg</source>|' /workspaces/dsg/coverage.xml
	genbadge coverage -i /workspaces/dsg/coverage.xml


ruff: ## Format Python code with Ruff
	ruff check --fix --exit-non-zero-on-fix --show-fixes $(SERVICE_PATH)
	ruff check --fix --exit-non-zero-on-fix --show-fixes $(TESTS_PATH)