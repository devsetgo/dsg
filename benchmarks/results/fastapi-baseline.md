# Benchmark: fastapi-baseline

- date: 2026-10-18T15:12:16-04:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R50000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/pypi/check`) | 1577.97 | 3.31ms | 5.38ms | 10.69ms | 0 |
| result (`/pypi/check/11111111-2222-3333-4444-555555555555`) | 531.74 | 45.41ms | 63.49ms | 78.53ms | 0 |
| health (`/api/health/status`) | 3278.34 | 2.09ms | 3.33ms | 6.24ms | 0 |

## Setup
- App: the pre-rewrite FastAPI app (`dev` @ 2493478a), `uvicorn src.main:app --workers 4 --log-level warning`, Python 3.14.8.
- DB: file SQLite (`DB_DRIVER=sqlite`; in-memory would give each worker its own DB) with one stored check of 3 packages.
- Pages render the old AdminLTE templates. `result` is a DB read plus a template render.
- None of these endpoints call PyPI.
