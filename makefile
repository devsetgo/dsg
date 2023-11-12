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
WORKERS = 8

VENV_PATH = _venv
REQUIREMENTS_PATH = requirements.txt
DEV_REQUIREMENTS_PATH = requirements/dev.txt

.PHONY: install run_prod run_dev help black isort autoflake

autoflake:
	autoflake --in-place --remove-all-unused-imports -r $(SERVICE_PATH)

black:
	black $(SERVICE_PATH)
	black $(TESTS_PATH)

cleanup: isort black autoflake

compile:
	gcc -shared -o http_request.so http_request.c -lcurl -fPIC

flake8:
	flake8 --tee . > _flake8Report.txt

help:
	@echo "Available targets:"
	@echo "  install       - Install required dependencies"
	@echo "  prod      	   - Run the FastAPI application in production mode"
	@echo "  dev           - Run the FastAPI application in development mode with hot-reloading"
	@echo "  create_tables - Create the necessary tables in the database"
	@echo "  black         - Format code using black"
	@echo "  isort         - Sort imports using isort"
	@echo "  autoflake     - Remove unused imports and variables"

isort:
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)

install:
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

dev:
	${DEV_SERVER} --port ${PORT} --reload

prd:
	${PROD_SERVER} --port ${PORT} --workers ${WORKERS}

test:
	pre-commit run -a
	pytest
	sed -i 's|<source>/workspaces/DevSetGo_Toolkit</source>|<source>/github/workspace/DevSetGo_Toolkit</source>|' /workspaces/DevSetGo_Toolkit/coverage.xml
	coverage-badge -o coverage.svg -f




