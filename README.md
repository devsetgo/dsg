
[![Coverage fury.io](coverage-badge.svg)](https://github.com/devsetgo/dsg)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)

# DevSetGo.com

My personal website and blog built with FastAPI. Versioned with CalVer (`YY.MM.DD`).

## Features

- **Blog** — posts with AI-generated tags, summaries, and mood analysis
- **Notes** — personal notes with OpenAI-powered analysis
- **Web Links** — curated link collection with AI-generated titles and summaries
- **PyPI Checker** — dev tool to check package versions and vulnerabilities
- **PDF Tools** — OCR and PDF processing via ocrmypdf
- **GitHub OAuth** — authentication via GitHub SSO
- **Admin panel** — user and content management

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Granian (ASGI) |
| Database | PostgreSQL (prod) / SQLite (dev/test) |
| ORM | SQLAlchemy (async) + Alembic |
| Auth | GitHub OAuth via fastapi-sso, PyJWT |
| AI | OpenAI (chat completions) |
| Deployment | Docker + Traefik reverse proxy |

## Configuration

Copy `env-files/.env.sample` to `.env` and fill in the values.

```bash
cp env-files/.env.sample .env
```

Key environment variables:

| Variable | Description | Default |
|---|---|---|
| `RELEASE_ENV` | Environment (`dev`, `test`, `prd`) | `prd` |
| `DB_DRIVER` | `postgres`, `sqlite`, or `memory` | `memory` |
| `OPENAI_KEY` | OpenAI API key (restricted to chat completions) | — |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | — |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app secret | — |
| `GITHUB_TOKEN` | GitHub personal access token | — |
| `SESSION_SECRET_KEY` | Secret for session cookie signing | random |
| `LOG_DIAGNOSE` | Loguru variable capture in tracebacks | `False` |
| `LOG_BACKTRACE` | Loguru extended backtraces | `False` |
| `HEALTH_STATUS_ENDPOINT` | Enable `/api/health/status` | `True` |
| `HEALTH_UPTIME_ENDPOINT` | Enable `/api/health/uptime` | `True` |
| `HEALTH_HEAPDUMP_ENDPOINT` | Enable `/api/health/heapdump` | `False` |

> **Security note:** Keep `HEALTH_HEAPDUMP_ENDPOINT=False` in production. Keep `LOG_DIAGNOSE` and `LOG_BACKTRACE` set to `False` in production — both can expose sensitive values in tracebacks.

## Development Setup

### Using the devcontainer (recommended)

Requires VS Code with the Dev Containers extension.

1. Open the repo in VS Code
2. Reopen in container when prompted
3. Copy and configure `.env`:
   ```bash
   cp env-files/.env.sample .env
   ```
4. Run the app:
   ```bash
   uvicorn src.main:app --reload --port 5000
   ```

### Local setup

```bash
python -m venv _venv
source _venv/bin/activate
pip install -r requirements/dev.txt
cp env-files/.env.sample .env
uvicorn src.main:app --reload --port 5000
```

## Running Tests

```bash
pytest
```

## Docker Deployment

The production image is `mikeryan56/dsg:<version>`. See `docker-compose/` for the server compose file and `.env.sample`.

```bash
cd docker-compose
cp .env.sample .env   # fill in production values
docker compose up -d
```

The app runs behind Traefik on port 5000 internally, exposed via HTTPS on the standard ports.

## Database Migrations

Alembic manages schema migrations.

| Command | Description |
|---|---|
| `make alembic-current` | Show current applied migration |
| `make alembic-history` | List all migrations |
| `make alembic-rev` | Generate a new migration from model changes |
| `make alembic-migrate` | Apply pending migrations |
| `make alembic-downgrade` | Roll back to a previous revision |

### Workflow

1. Edit models in `src/db_tables.py`
2. Generate migration: `make alembic-rev`
3. Review the file in `alembic/versions/`
4. Apply: `make alembic-migrate`

> Always review generated migrations before applying to production and back up the database first.

### Drop all tables (PostgreSQL — dev use only)

```sql
DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
```

## Git Config

```bash
git config --global credential.helper store
git config --global user.name "Mike Ryan"
git config --global user.email "mikeryan56@gmail.com"
```
