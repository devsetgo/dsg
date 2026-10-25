# Project status: Robyn rewrite

_Last updated 2026-10-25. Branch `robyn-rewrite` (from `dev`), pushed to origin._

## Where things stand

The rewrite is **done and pushed**. `dsg` is now a single-purpose public tool. You paste a
`requirements.txt`, pick a target Python (3.8–3.15) and platform, and it resolves the file the way pip does. The result
shows upgrades, downgrades, conflicts, held-back packages, source builds, and known vulnerabilities for both the pinned
and the new version.

- **Stack:** Robyn 0.88 or Granian 2.8 (RSGI) behind the same handlers (`src/routes/`, adapters in `src/main.py` and
  `src/rsgi.py`; `make run-dev` uses Granian), SQLite via devsetgo_lib and Alembic (one baseline migration), pydantic-schemaforms 26.4.1, an
  MDB UI Kit layout ported from mrie, and htmx.
- **Resolver:** `src/resolver/` uses resolvelib, packaging, PEP 691 JSON and PEP 658 metadata. Its results match
  `uv pip compile` package-for-package on the 96-line sample, for 3.10 and 3.12.
- **Tests:** 227 pass (every app test runs against both servers), 3 network tests are deselected by default, coverage is 99% with branch coverage on. The
  remaining gaps (`db_init.py` file-database PRAGMAs, the opt-in access log in `main.py`) are exercised by subprocess
  tests that coverage can't see. `make test` (pre-commit and
  pytest) is clean inside the rebuilt devcontainer.
- **Lint:** ruff and black 26.10.1 are clean.
- **Docker:** the image is 457 MB and runs migrations on startup. It reported healthy after 3 fresh starts with 4
  processes.
- **`dsg-pr-check`:** all findings from both runs (2026-10-18 and 2026-10-23) are fixed. The fixes include:
  - credential redaction;
  - private history by default (`PUBLIC_HISTORY`);
  - concurrency, queue and per-IP limits;
  - safe error messages;
  - Stats lists only packages that exist on PyPI, so private names never appear;
  - the client IP for rate limiting comes from proxy-appended `X-Forwarded-For` entries only
    (`FORWARDED_PROXY_HOPS`, default 1 for Traefik);
  - queue places are claimed atomically when a check is accepted;
  - SRI hashes on the CDN scripts and CSS (bump the hash along with any version);
  - 301 redirects for the old `/pypi/*` URLs;
  - an aligned Release Drafter / ai-pr-assistant label taxonomy.

- **Performance** (details in `benchmarks/results/README.md`): warm checks take 0.3 s instead of 2-4 s, and 8 at
  once take 3-4 s instead of 13 s, because parsed releases and Requires-Python answers are cached. Granian can't
  serve Robyn and was slower than uvicorn with the FastAPI shim. Set `PROCESSES` to the container's CPU count.

- **Production host:** 8 vCPU, 32 GB, shared with a couple of low-use Python apps. The image defaults to
  `PROCESSES=8 WORKERS=1`. Rate limits and queues are per process, so the effective per-IP limit can reach 8x
  `CHECKS_PER_MINUTE_PER_IP`.

- **Removed as dead:** the `RELEASE_ENV` setting (nothing read it) and a never-false `if` in the lock-file writer.
  Found with `dsg-coverage-check` plus a 6,000-case random search of package sets to confirm each claim.

## Next steps

1. **Commit and open the PR with `/dsg-commit`.** Mark it **breaking**: every old route is gone, and the Postgres schema
   is replaced by a fresh SQLite database with no data migration.
2. **Deploy.** Compose now needs the `sqlite-volume`, and the `postrgresql_db_network` is gone. Run only one container,
   because SQLite can't take writers on more than one host.

## Open TODOs

- **`TODO_TASKS.md`:** nothing open.
- **Release Drafter:** the workflow now sets `config-name: release-drafter.yaml`. Confirm the first run after merge
  picks up the categories (`gh` isn't installed in the devcontainer, so past runs weren't checked).
- **Old `.env`:** the pre-rewrite `.env` is backed up as `.env.pre-rewrite` (gitignored). It holds old secrets
  (GitHub OAuth, OpenAI, Postgres); delete it once you no longer need them.
- **Python 3.15:** wait for Robyn to publish cp315 wheels. 0.88.0 has none, and the fallback on 3.15 is robyn 0.69.0,
  an sdist that needs Rust and pulls in vulnerable jinja2 and orjson.
- **Optional benchmark follow-ups:** see `benchmarks/results/README.md`. With the same code, FastAPI with uvicorn
  matched or beat Robyn. The new app's speed comes from the rewrite, not the framework.
- **Retention:** there's no purge job, so checks are kept forever. Decide on a retention policy.

## Issues worth reporting upstream (found while dogfooding)

- **pydantic-schemaforms 26.4.1**
  - Defaults aren't pre-selected unless passed as `form_data`.
  - `hx_post=` is emitted literally instead of as `hx-post`.
  - A checkbox with a True default can't be switched off.
  - The Bootstrap markup is slightly off under MDB: the radio fieldset and the textarea label.
- **devsetgo_lib** (rechecked on 2026.10.24.1)
  - Still open: `get_table_names()` lists the metadata's models, not the tables in the database.
  - Still open: `execute_one(text("SELECT …"))` returns `"complete"` instead of rows.
  - Still open: read errors come back as `DatabaseErrorResult` values that are easy to mistake for "not found".
  - Not rechecked: the `:memory:` StaticPool shares one connection, so concurrent sessions can silently lose writes.
  - Fixed in 2026.10.18.1: there's a Robyn health router (`dsg_lib.robyn_functions.system_health_endpoints`).
  - Fixed in 2026.10.24.1: `create_health_router` no longer starts `tracemalloc` unless heapdump is enabled
    (this app's `tracemalloc.stop()` workaround is gone), and the health routes log at DEBUG, so
    `/api/health/status` holds ~19.5k req/s at the default INFO level instead of ~13k.
- **resolvelib 1.2.1** (also unfixed on `main`; pip vendors the same code)
  - `_has_route_to_root` in `_build_result` recurses with no visited set. A dependency cycle among candidates that
    backtracking left disconnected raises `RecursionError` after a successful resolution: 24 of 6,000 random
    5-package sets. `service._build_result` is an iterative copy. It matched upstream on all 5,133 resolutions where
    upstream didn't crash. Drop it once upstream is fixed.
  - The result graph and criteria keep parents that `Result.mapping` dropped. `service.py` filters them out of
    "required by" and held-back reasons.
- **Robyn 0.88.0**
  - All `--processes N` workers `accept()` on one cloned listening socket, so connections concentrate on a few of
    them (4 of 8 did all the work with keep-alive clients). Separate single-process instances on the same port
    (`SO_REUSEPORT`) spread better: 7 of 8, about 19% more throughput.
  - A single-process server ignores SIGTERM and SIGINT (the shutdown handler never runs, and the process stays up
    until SIGKILL); with `--processes` > 1 the parent kills its children and exits in ~250 ms.
  - `request.form_data` is empty for urlencoded bodies.
  - On a busy port, `start()` prompts on stdin forever; it's disabled here with `_check_port=False`.
  - A second instance silently shares the port.
  - The `--dev` reloader restarts on *any* file write under the app folder, with no excludes.
  - `@app.exception` returns `None`.
- **mrie:** the same SQLite PRAGMA-order bug fixed here (set `busy_timeout` *before* `journal_mode=WAL`). Without it,
  processes starting together on a fresh database fail with "database is locked".

## Gotchas

- **Dev reload:** `make run-dev` runs Granian with `--reload-paths` on `src/`, `templates/`, `static/` and `alembic/` on
  purpose. A reloader watching the whole folder would restart on every check's SQLite write and kill the check (Robyn's
  `--dev` does exactly that, so `make run-dev-robyn` uses watchfiles instead).
- **RSGI differences:** multipart/form-data bodies aren't parsed, bodies are capped at 1 MiB, and there's no app-level
  access log (use `granian --access-log`). Tests drive the RSGI app in-process with `tests/rsgi_client.py`.
- **Stray servers:** a stale Robyn process can keep answering on the same port, so stop old servers (`make kill`).
- **Test logs:** tests log to a temp directory, not `log/`.
- **Root-owned file:** `htmlcov/` has one left over from an old container run, which is why the HTML coverage report
  is off by default. `sudo rm -rf htmlcov` clears it.
- **OCR files:** `pdf/` still holds the old OCR PDFs. It's gitignored; delete it when you're sure they aren't needed.
- **Benchmarks:** `benchmarks/run.sh` needs wrk2 at `~/wrk2/wrk`, which isn't in the devcontainer. Building it from
  `giltene/wrk2` here printed a linker warning (`bytecode.o: string table is corrupt`) and then every run died with a
  Lua `PANIC`. Fix: in `deps/luajit/src` run `./luajit -b ../../../src/wrk.lua ../../../obj/bytecode.c`, compile that
  to `obj/bytecode.o` with gcc, delete `wrk` and run `make` again. wrk2 also aborts with an hdr_histogram assertion
  about 1 run in 8, even against a trivial server; `run.sh` retries those.
  `benchmarks/fastapi_shim.py` needs `fastapi` and `uvicorn`, which aren't app dependencies.
