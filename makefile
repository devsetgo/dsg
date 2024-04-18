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

.PHONY: autoflake black cache cleanup compile dev flake8 gdev gprd grdev help install install-dev isort prd test

alembic-migrate: # migrate database using alembic
	alembic upgrade head

alembic-rev: # Create revision database using alembic
	@read -p "Enter revision name: " name; \
	alembic revision --autogenerate -m "$$name"
	
autoflake:  # Remove unused imports and variables
	autoflake --in-place --remove-all-unused-imports -r $(SERVICE_PATH)

black:  # Format code using black
	black $(SERVICE_PATH)
	black $(TESTS_PATH)

cache:  # Clean pycache
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '.pytest_cache' -exec rm -rf {} +

cleanup: isort black autoflake  # Run isort, black, and autoflake

compile:  # Compile http_request.c into a shared library
	gcc -shared -o http_request.so http_request.c -lcurl -fPIC

dev:  # Run the FastAPI application in development mode with hot-reloading
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --reload

flake8:  # Run flake8 and output report
	flake8 --tee . > _flake8Report.txt

gdev:  # Run the FastAPI application in development mode with hot-reloading using granian
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --reload

gprd:  # Run the FastAPI application in production mode using granian
	granian --interface asgi ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS}

grdev:  # Run the FastAPI application in development mode with hot-reloading using granian and rsgi interface
	granian --interface rsgi ${SERVICE_PATH}.main:app --port ${PORT} --reload

help:  # Display available targets
	@echo "Available targets:"
	@echo "  autoflake     - Remove unused imports and variables"
	@echo "  black         - Format code using black"
	@echo "  cache         - Clean pycache"
	@echo "  cleanup       - Run isort, black, and autoflake"
	@echo "  compile       - Compile http_request.c into a shared library"
	@echo "  dev           - Run the FastAPI application in development mode with hot-reloading"
	@echo "  flake8        - Run flake8 and output report"
	@echo "  gdev          - Run the FastAPI application in development mode with hot-reloading using granian"
	@echo "  gprd          - Run the FastAPI application in production mode using granian"
	@echo "  grdev         - Run the FastAPI application in development mode with hot-reloading using granian and rsgi interface"
	@echo "  install       - Install required dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  isort         - Sort imports using isort"
	@echo "  prd           - Run the FastAPI application in production mode"
	@echo "  test          - Run tests and generate coverage report"

install:  # Install required dependencies
	$(PIP) install -r $(REQUIREMENTS_PATH)

install-dev:  # Install development dependencies
	$(PIP) install -r $(DEV_REQUIREMENTS_PATH)

isort:  # Sort imports using isort
	isort $(SERVICE_PATH)
	isort $(TESTS_PATH)

prd:  # Run the FastAPI application in production mode
	uvicorn ${SERVICE_PATH}.main:app --port ${PORT} --workers ${WORKERS}

test:  # Run tests and generate coverage report
	pre-commit run -a
	PYTHONPATH=. pytest
	sed -i 's|<source>/workspaces/dsg</source>|<source>/github/workspace/dsg</source>|' /workspaces/dsg/coverage.xml
	coverage-badge -o coverage.svg -f
