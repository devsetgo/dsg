# Benchmark: robyn-4x1-adapters-2026.10.24.1

- date: 2026-10-24T23:58:15+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 4650.70 | 2.09ms | 3.52ms | 325.12ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 5743.29 | 1.42ms | 2.30ms | 5.43ms | 0 |
| health (`/api/health/status`) | 19960.96 | 1.06ms | 1.61ms | 2.17ms | 0 |
