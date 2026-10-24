# Robyn vs FastAPI

Measured with wrk2 (`benchmarks/run.sh`): `-t4 -c64 -d20s`. Max throughput is taken at an offered rate of
20,000 req/s, and latency at a fixed 300 req/s. Host: WSL2, 20 CPUs, Python 3.14.8. All servers ran 4 processes
against the same file SQLite database, holding one stored check of 3 packages. None of these endpoints call PyPI.

## Same code, different framework (the fair comparison)

`benchmarks/fastapi_shim.py` serves the three endpoints through the *same* templates, forms, DB layer and caches
as the Robyn app.

| endpoint | Robyn 0.88, 4 proc × 1 worker | FastAPI 0.146 + uvicorn 0.54, 4 workers (uvloop, httptools) |
|---|---|---|
| form `/check` | 6,817 req/s · p99 5.9 ms | **7,401** req/s · p99 9.7 ms |
| result `/check/<id>` | 7,665 req/s · p99 2.9 ms | **12,304** req/s · p99 3.9 ms |
| health `/api/health/status` | 18,255 req/s · p99 2.4 ms | 19,962 req/s · p99 2.6 ms (at the 20k offered cap) |

Robyn **was not faster** here. Throughput is equal or lower, with somewhat lower tail latency at a light load.
Once a request does any real Python work (Jinja rendering, pydantic, SQLAlchemy), the Rust HTTP layer no longer
dominates the cost. Robyn's edge shows mainly on trivial endpoints, and even there uvicorn with uvloop and
httptools keeps up.

Robyn configuration notes, from the runs in this directory:
- **Workers per process.** `--workers 1` beat `--workers 2`: 6,586 vs 5,608 req/s on the result page.
- **Middleware.** Robyn's per-request `before_request`/`after_request` middleware costs about 15% on the form page.
  The access log is therefore opt-in (`ACCESS_LOG=True`).

## Old app vs new app (`fastapi-baseline.md` vs `robyn-4proc-1worker.md`)

| endpoint | old FastAPI app | new Robyn app |
|---|---|---|
| form | 1,578 | 6,817 |
| result | 532 | 7,665 |
| health | 3,278 | 18,255 |

Most of that gain comes from the rewrite, not the framework:
- no session, GZip or access-log middleware;
- a far smaller template;
- a cached stats summary;
- an in-process cache of finished checks, which never change.

The shim gets the same gains on FastAPI.

## Where time actually goes

A real check is dominated by PyPI round trips and resolver CPU, not the web framework:

| run (6 requirements → 73 packages, with boto3/awscli backtracking) | time |
|---|---|
| cold cache | ~16 s |
| warm SQLite cache | 3.3 s |
| warm SQLite cache + in-process LRU in front | 0.42 s |
| 8 concurrent warm checks | 4.9 s total |

## 2026-10-24: Granian, process count, and the resolver

Same host and method as above (`-R20000` offered). The machine ran about 22% slower than on 2026-10-18: uvicorn's
form and result numbers fell by that much against its own earlier run. Compare only rows from the same day.
Robyn 0.88, FastAPI 0.143, uvicorn 0.54, Granian 2.8.4 (ASGI, uvloop), all with 4 workers.

| endpoint | Robyn 4 proc × 1 | Robyn 2 proc × 2 | uvicorn 4w | Granian 4w |
|---|---|---|---|---|
| form `/check` | 4,422 · p99 6.7 ms | 2,987 | **5,756** · p99 3.3 ms | 5,235 |
| result `/check/<id>` | 5,944 · p99 3.5 ms | 4,741 | **10,381** · p99 3.2 ms | 8,720 |
| health `/api/health/status` | 11,198 (see below) | 8,257 | 19,962 (the offered cap) | 19,961 (the offered cap) |

**Granian does not help.** It only serves ASGI/RSGI/WSGI apps, so it can't run Robyn (Robyn brings its own server).
Next to uvicorn, with the same FastAPI shim, it was 9% slower on the form and 16% slower on the result page, and
equal on health. On this workload FastAPI with uvicorn was 30-75% faster than Robyn on the two page endpoints, which
matches the earlier comparison above.

**Process count.** Robyn scales about linearly: the result page served 2,558 req/s with 1 process, 4,885 with 2,
5,294 with 4 and 9,830 with 8 (noisy; the load generator competes for CPU above that). Set `PROCESSES` to the CPUs
the container actually has; the image default of 2 is conservative. One worker per process beats two.

**dsg_lib's health route logs an INFO line per call.** With `LOGGING_LEVEL=INFO` Robyn served 13,000 req/s on health;
with `WARNING`, 19,900 (the cap). Two rounds each. Real traffic is a Docker healthcheck every 90 s, so this only
matters for benchmarks and aggressive uptime monitors.

### Resolver CPU (the part users wait for)

A profile of a warm check on `tests/fixtures/sample_requirements.txt` (96 lines → 114 packages) showed two thirds
of the time in re-parsing: `SpecifierSet(requires_python)` for every file of every release (~130,000 calls on 20
distinct strings) and wheel-filename parsing for every release of every project (~120,000 filenames). Both results
are now cached (`environment._python_satisfies`, `PyPIIndex._parsed`). The output is byte-identical on the sample
for 3.10/3.12 in both modes, and the cache costs about 3 MB per 114 projects.

| real server, 4 processes, live PyPI | before | after |
|---|---|---|
| first check (cold cache) | 7.9-8.1 s | 7.3 s |
| one warm check | 1.95-3.9 s | 0.33 s |
| 8 warm checks at once | 13.0-13.5 s | 2.9-4.1 s |

A cold check is bound by PyPI round trips, so it barely moved.

### Sizing for the production host (8 vCPU, 32 GB, shared with a couple of low-use apps)

The image now defaults to `PROCESSES=8 WORKERS=1`. Memory is not a constraint: a process that has run checks holds
280-420 MB, an idle one about 82 MB, so 8 busy processes stay under 3.5 GB.

**Robyn does not spread work evenly across processes.** All processes `accept()` on one cloned listening socket, and
a few of them win most connections. With 16 keep-alive connections (what a proxy such as Traefik holds open) and
real checks:

| layout | checks/s (160 checks) | processes that did work |
|---|---|---|
| `--processes 8` (shared socket) | 5.7 | 4 of 8 |
| 8 separate `--processes 1` instances on one port | 6.8 | 7 of 8 |

Separate instances get their own listening sockets (Robyn sets `SO_REUSEPORT`), so the kernel hashes connections
across them. That is about 19% faster here, but it needs a supervisor, and a single-process Robyn does not exit
on SIGTERM or SIGINT (see PROJECT_STATUS.md), so it was not adopted. Page endpoints with many connections still
scaled well with processes (the result page: 5,294 req/s at 4, 9,830 at 8).

**SQLite write contention under bursts.** 24 checks finishing at once produced `database is locked` (HTTP 500)
even with a 5 s busy timeout: `store_report` inserted the packages one statement at a time and held the single
write lock for ~120 ms, and SQLite's retry loop is not fair. It is now one `executemany` (8 ms). After the change,
bursts of 24 concurrent checks across 4 and 8 processes ran with no locked errors.
