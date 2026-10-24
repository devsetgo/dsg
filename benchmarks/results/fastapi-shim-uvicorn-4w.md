# Benchmark: fastapi-shim-uvicorn-4w

- date: 2026-10-18T15:59:16-04:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 7401.31 | 1.89ms | 6.84ms | 9.65ms | 0 |
| result (`/check/71f48dc9-51e7-4c1d-b79f-745e7ebbc966`) | 12303.82 | 1.38ms | 2.08ms | 3.90ms | 0 |
| health (`/api/health/status`) | 19962.23 | 1.15ms | 1.77ms | 2.55ms | 0 |
