# Variables
PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest

SERVICE_PATH = src
TESTS_PATH = src/tests
SQLITE_PATH = _sqlite_db
LOG_PATH = log

VENV_PATH = _venv
REQUIREMENTS_PATH = requirements.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt


.PHONY: autoflake clean flake8-report format help install install-dev isort migrate run-clean run-dev run-prd spring-clean test venv-create

run-clean:
	./_scripts/rm_db_log.sh $(CURDIR)/$(SQLITE_PATH) $(CURDIR)/$(LOG_PATH)
	uvicorn $(SERVICE_PATH).main:app --reload --port 5000

autoflake:
	autoflake --in-place --remove-all-unused-imports -r $(SERVICE_PATH)

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	rm -rf .mypy_cache

flake8-report:
	./_scripts/flake8.sh

format:
	black $(SERVICE_PATH)
	black $(TESTS_PATH)

help:
	@echo "Available commands:"
	@echo "  venv-create   Create a virtual environment"
	@echo "  install       Install dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  isort         Sort imports using isort"
	@echo "  autoflake     Run autoflake"
	@echo "  test          Run tests via pre-commit and pytest"
	@echo "  format        Format code using black"
	@echo "  spring-clean  Run all formatting and cleanup"
	@echo "  migrate       Migrate the database with Alembic"
	@echo "  run-dev       Run the application with Uvicorn"
	@echo "  run-prd       Run the application with Gunicorn"
	@echo "  clean         Clean up pycache and compiled Python files"
	@echo ""

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

isort:
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)

migrate:
	$(PYTHON) alembic upgrade head

run-dev:
	uvicorn $(SERVICE_PATH).main:app --reload --port 5000




run-prd:
	gunicorn $(SERVICE_PATH).main:app -w 4 -k uvicorn.workers.UvicornWorker

spring-clean: clean isort autoflake format flake8-report

test:
	pre-commit run -a
	$(PYTEST) --cov=$(SERVICE_PATH) --cov-report=html --cov-report=xml -ra --tb=short
	coverage-badge -o coverage.svg -f

venv-create:
	$(PYTHON) -m venv $(VENV_PATH)
