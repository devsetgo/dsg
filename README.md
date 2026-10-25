[![Coverage](coverage-badge.svg)](https://github.com/devsetgo/dsg)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/release/python-3140/)

# DevSetGo: Python dependency resolver

Paste a `requirements.txt`, pick the Python version and platform you deploy on, and get the newest set of
versions that install together there. If no such set exists, you get an explanation of why.

It resolves the way pip does:
- **Same engine.** [resolvelib](https://github.com/sarugaku/resolvelib) is the backtracking resolver inside pip.
- **Same rules.** [packaging](https://packaging.pypa.io) handles PEP 440 versions and specifiers, PEP 508 markers, and wheel tags.
- **Same data.** It reads PyPI's JSON Simple API (PEP 691) and each wheel's published metadata (PEP 658).

The difference is that it answers for a **target** interpreter and platform, not the one it runs on:

- `Requires-Python` excludes releases the target can't install, so `numpy` on 3.10 resolves to 2.2.x.
- Markers such as `; python_version < "3.11"` and `; sys_platform == "win32"` are evaluated for the target.
- Only wheels whose tags match the target count, with the sdist as a fallback, as pip does.
- Extras (`fastapi[all]`) pull in their own dependencies, and yanked releases are skipped unless pinned exactly.

Each result shows:
- the re-pinned `requirements.txt` and a full lock of every package;
- known vulnerabilities from PyPI's advisory data;
- for every package that couldn't reach its newest compatible release, the requirement that held it back.
  For example, `awscli 1.46.1 requires docutils<=0.19,>=0.18.1`, or `fastapi 0.146.0 requires pydantic>=2.9.0, but pydantic 1.10.26 is selected`.

There are two modes:
- **Upgrade** drops your version pins and keeps names, extras and markers.
- **Validate** keeps your pins and tells you whether the file installs on the target, and why not if it doesn't.

On the 96-line sample in `tests/fixtures/`, the result matches `uv pip compile --python-version X` package-for-package (114 packages) for both 3.10 and 3.12.

## Stack

| Layer | Technology |
|---|---|
| Web | [Robyn](https://robyn.tech) (Rust runtime, multi-process) or [Granian](https://github.com/emmett-framework/granian) through RSGI, behind the same handlers |
| Forms | [pydantic-schemaforms](https://github.com/devsetgo/pydantic-schemaforms) |
| Database | SQLite (WAL) via [devsetgo_lib](https://github.com/devsetgo/devsetgo_lib) + SQLAlchemy async, Alembic migrations |
| UI | MDB UI Kit (Bootstrap 5), layout after [mdbootstrap/bootstrap-5-admin-template](https://github.com/mdbootstrap/bootstrap-5-admin-template), htmx |
| Versioning | [bumpcalver](https://github.com/devsetgo/bumpcalver) (CalVer) |
| PRs | [ai-pr-assistant](https://github.com/devsetgo/ai-pr-assistant) |

## Layout

```
src/
  web.py             framework-neutral Request/Reply, route table and matcher
  routes/            the handlers, written against web.py: pages.py (HTML), api.py (JSON), errors.py;
                     health.py is dsg_lib's Robyn health router
  main.py            Robyn adapter: routes, static files, startup/shutdown, error handler
  rsgi.py            Granian adapter (RSGI): the same routes, static files, health, lifecycle hooks
  logs.py            logging setup shared by both
  forms.py           pydantic-schemaforms form for a check
  checks.py          check lifecycle: create row -> resolve in background -> store report
  resolver/          pure resolver, no web or DB imports:
    parse.py           requirements.txt -> PEP 508 requirements (+ reported issues)
    environment.py     target Python/platform -> marker environment + wheel tags
    index.py           async PyPI client, caches, sync bridge for the resolver thread
    provider.py        resolvelib provider (pip's candidate/extras semantics)
    explain.py         conflict and held-back explanations
    service.py         resolve_requirements() -> ResolutionReport
  pypi_cache.py      SQLite-backed cache store for PyPI responses
templates/, static/  MDB layout (base.html), pages, htmx fragments
benchmarks/          wrk2 scripts and results (Robyn, FastAPI, Granian)
```

## Running

```bash
uv venv .venv -p 3.14 && uv pip install -p .venv/bin/python -r requirements/dev.txt
cp env-files/.env.sample .env
make run-dev            # Granian (RSGI) with hot reload on :5000; migrates sqlite_db/dsg_dev.db first
make run-granian PROCESSES=8      # Granian, like production
make run-dev-robyn      # the same app on Robyn, with hot reload
make run PROCESSES=8 WORKERS=1    # Robyn, like production
```

The handlers in `src/routes/` know nothing about the server. `src/main.py` connects them to Robyn and `src/rsgi.py` to
Granian's native RSGI interface. Differences on RSGI: multipart/form-data bodies are not parsed (the form posts
urlencoded), request bodies are capped at 1 MiB, and there is no app-level access log (use Granian's `--access-log`).
Granian reloads on changes under `src/`, `templates/`, `static/` and `alembic/` only, so a check's writes to the
database never restart it.

Health checks: `GET /api/health/status` returns `{"status": "UP"}` and `GET /api/health/uptime` returns
`{"uptime": {"Days", "Hours", "Minutes", "Seconds"}}`. `HEALTH_STATUS_ENDPOINT` and `HEALTH_UPTIME_ENDPOINT` switch them off.

Every setting is in `env-files/.env.sample`, with its default. `DB_DRIVER=memory` is for the test suite only
(the reason is in `src/settings.py`).

A scripting API is also available:

```bash
curl -s localhost:5000/api/check -H 'content-type: application/json' \
  -d '{"requirements": "numpy==1.26.2\npandas", "python_version": "3.10", "mode": "upgrade"}'
```

The response is a JSON report. The status is 200 when the set resolves and 409 when there's a conflict, with the
explanation in the body. A 400 means the body isn't a JSON object, and a 422 means it failed validation, with the
details in `errors`. A 429 means the rate limit or the queue is full, and a 502 means the check itself failed (PyPI
unreachable, internal error), with the reason in `error`. A 500 means the check couldn't be stored.

## Privacy and limits

- **What's stored.** Every check is stored in SQLite: the submitted file, the report, the client IP and the user agent.
  There is no automatic purge, so checks are kept until the database is cleared.
- **Credentials.** They are stripped from URLs before anything is stored. For example,
  `--extra-index-url https://deploy:<token>@host/simple` is saved and shown as `https://****@host/simple`.
- **Who can see results.** Each result is reachable only through its own link (a random UUID). The Recent Checks list is
  off unless `PUBLIC_HISTORY=True`, because a pasted file can name private or internal packages. The Stats page shows
  totals plus the most-checked packages, but only names that exist on PyPI, so a private package never appears there.
- **Abuse limits.** Each worker process runs at most `MAX_CONCURRENT_CHECKS` resolutions at once. It queues up to
  `MAX_QUEUED_CHECKS` more and answers HTTP 429 beyond that. Each client IP is limited to `CHECKS_PER_MINUTE_PER_IP`
  checks per minute. These counters are kept per process, so the effective per-IP limit can reach `PROCESSES` times that
  (8 by default), and a hard global limit belongs in the proxy. The client IP is
  read from `X-Forwarded-For`, counting `FORWARDED_PROXY_HOPS` entries from the right (default 1, for Traefik), so a
  header the client makes up can't dodge the limit.
- **Dead checks.** A check that stops sending its heartbeat for 30 seconds (process restart, crash) is shown as failed
  instead of polling forever.

## Tests

```bash
make test            # pre-commit + pytest (fake PyPI, in-memory DB, no network) + badges
make test-network    # a few checks against the real PyPI
```

## Docker

```bash
make docker-build && make docker-run
```

The entrypoint runs `alembic upgrade head` before starting the server. Logs and the SQLite file are volumes; see `docker-compose.yml`.
Run one container only, because SQLite can't be shared by writers on different hosts.

The image starts 8 processes (`PROCESSES=8`, one worker each; one worker beat two in the benchmarks), sized for an 8 vCPU
host. `SERVER=robyn` is the default; set `SERVER=granian` to serve the RSGI app instead.

## Benchmarks

`benchmarks/run.sh` drives [wrk2](https://github.com/giltene/wrk2) against the endpoints that don't call PyPI. It records the
maximum throughput, plus latency at a fixed rate. Results and setup details are in `benchmarks/results/`.
