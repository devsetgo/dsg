# Benchmark: robyn-4x1-dsglib-2026.10.24.1

- date: 2026-10-24T23:29:23+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 4176.50 | 2.04ms | 3.22ms | 7.20ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 5661.28 | 1.45ms | 2.35ms | 5.34ms | 0 |
| health (`/api/health/status`) | 19962.05 | 0.98ms | 1.52ms | 2.08ms | 0 |
