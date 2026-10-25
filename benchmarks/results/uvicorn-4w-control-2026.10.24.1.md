# Benchmark: uvicorn-4w-control-2026.10.24.1

- date: 2026-10-24T23:45:09+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 6282.57 | 1.84ms | 2.55ms | 3.49ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 10142.18 | 1.42ms | 2.11ms | 3.20ms | 0 |
| health (`/api/health/status`) | 19961.31 | 1.10ms | 1.68ms | 2.24ms | 0 |
