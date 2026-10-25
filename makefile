# =============================================================================
# Project Variables
# =============================================================================
REPONAME = dsg
APP_VERSION = 2026-10-24-001

# Python Configuration
PYTHON ?= $(shell if command -v python3.14 >/dev/null 2>&1; then echo python3.14; else echo python3; fi)
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest
ALEMBIC = $(PYTHON) -m alembic

# Path Configuration
SERVICE_PATH = src
TESTS_PATH = tests

# Server Configuration
HOST ?= 0.0.0.0
PORT ?= 5000
PROCESSES ?= 8
WORKERS ?= 1

# Requirements
REQUIREMENTS_PATH = requirements/prd.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt

# Benchmarks (wrk2: https://github.com/giltene/wrk2)
WRK ?= $(HOME)/wrk2/wrk
BENCH_URL ?= http://localhost:$(PORT)

# =============================================================================
# Safety Checks
# =============================================================================
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
.SUFFIXES:

.PHONY: help install install-dev format ruff black validate test test-network test-file \
	run run-dev run-dev-robyn run-granian migrate revision alembic-current alembic-history bench kill \
	docker-build docker-run docker-push docker-all bump bump-beta clean

# =============================================================================
# Default Target
# =============================================================================
help:  ## Display this help message
	@printf "\033[0;36m$(REPONAME) makefile\033[0m\n"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[0;36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[0;36m%-18s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup
install:  ## Install production dependencies
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:  ## Install development dependencies
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

##@ Code quality
ruff:  ## Lint and fix with ruff
	$(PYTHON) -m ruff check --fix --show-fixes $(SERVICE_PATH) $(TESTS_PATH)

black:  ## Format with black (what pre-commit runs)
	$(PYTHON) -m black $(SERVICE_PATH) $(TESTS_PATH)

format: ruff black  ## Run all formatters

validate:  ## Check style without changing files
	$(PYTHON) -m ruff check $(SERVICE_PATH) $(TESTS_PATH)
	$(PYTHON) -m black --check $(SERVICE_PATH) $(TESTS_PATH)

##@ Tests
test:  ## Run pre-commit and the test suite (no network), then update badges
	pre-commit run -a
	$(PYTEST) --junitxml=report.xml
	genbadge coverage -i coverage.xml
	genbadge tests -i report.xml

test-network:  ## Run the tests that hit the real PyPI
	$(PYTEST) -m network --no-cov

test-file:  ## Run one test file: make test-file FILE=test_resolver.py
	$(PYTEST) $(TESTS_PATH)/$(FILE) -v

##@ Run
# Granian serving src/rsgi.py (RSGI). It watches only the listed paths: a reloader
# that watched the whole folder would restart on every check's write to sqlite_db/
# and log/, killing the check that caused it.
GRANIAN = $(PYTHON) -m granian --interface rsgi --loop uvloop --no-ws --host $(HOST) --port $(PORT)

run-dev:  ## Run with hot reload on Granian (RSGI) against sqlite_db/dsg_dev.db
	DB_DRIVER=sqlite DB_NAME=dsg_dev $(ALEMBIC) upgrade head
	DB_DRIVER=sqlite DB_NAME=dsg_dev $(GRANIAN) --log-level info --reload \
		--reload-paths $(SERVICE_PATH) --reload-paths templates --reload-paths static \
		--reload-paths alembic $(SERVICE_PATH).rsgi:app

run-granian:  ## Run like production on Granian (RSGI): make run-granian PROCESSES=8
	$(ALEMBIC) upgrade head
	$(GRANIAN) --workers $(PROCESSES) --log-level warning --no-access-log $(SERVICE_PATH).rsgi:app

# The same app on Robyn. Not Robyn's --dev: its reloader restarts on a write to *any*
# file under the app's folder, so watchfiles watches only the code.
run-dev-robyn:  ## Run with hot reload on Robyn against sqlite_db/dsg_dev.db
	DB_DRIVER=sqlite DB_NAME=dsg_dev $(ALEMBIC) upgrade head
	DB_DRIVER=sqlite DB_NAME=dsg_dev PORT=$(PORT) $(PYTHON) -m watchfiles --target-type command \
		"$(PYTHON) -m $(SERVICE_PATH).main --log-level WARN" $(SERVICE_PATH) templates static alembic

run:  ## Run like production on Robyn: make run PROCESSES=8 WORKERS=1
	$(ALEMBIC) upgrade head
	PORT=$(PORT) $(PYTHON) -m $(SERVICE_PATH).main --processes $(PROCESSES) --workers $(WORKERS) --log-level WARN

kill:  ## Kill whatever is listening on PORT (a stale instance can share the port)
	@lsof -ti:$(PORT) | xargs -r kill -9 || true

##@ Database
migrate:  ## Apply migrations
	$(ALEMBIC) upgrade head

revision:  ## Autogenerate a migration: make revision NAME="add thing"
	$(ALEMBIC) revision --autogenerate -m "$(NAME)"

alembic-current:  ## Show the current revision
	$(ALEMBIC) current

alembic-history:  ## Show migration history
	$(ALEMBIC) history

##@ Benchmarks
bench:  ## wrk2 against a running server: make bench LABEL=robyn RESULT=/check/<id>
	WRK=$(WRK) benchmarks/run.sh $(LABEL) $(BENCH_URL) /check $(RESULT) /api/health/status

##@ Docker
docker-build:  ## Build the image
	docker build -t dsg:$(APP_VERSION) .

docker-run:  ## Run the image locally on port 5000
	docker run --rm -p 5000:5000 dsg:$(APP_VERSION)

docker-push:  ## Push the image to Docker Hub
	docker tag dsg:$(APP_VERSION) mikeryan56/dsg:$(APP_VERSION)
	docker push mikeryan56/dsg:$(APP_VERSION)

docker-all: docker-build docker-push  ## Build and push

##@ Release
bump:  ## Bump the CalVer version with bumpcalver and tag
	bumpcalver --build --git-tag

bump-beta:  ## Bump a beta version
	bumpcalver --build --beta

clean:  ## Remove caches and test artifacts
	find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml report.xml
