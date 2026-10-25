# Benchmark: uvicorn-4w-dsglib-2026.10.24.1

- date: 2026-10-24T23:32:26+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 5522.54 | 1.83ms | 2.61ms | 3.58ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 8519.82 | 1.43ms | 2.15ms | 3.21ms | 0 |
| health (`/api/health/status`) | 19962.03 | 1.09ms | 1.63ms | 2.12ms | 0 |
