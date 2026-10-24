# Benchmark: robyn-4proc-1worker

- date: 2026-10-18T16:03:53-04:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 6817.42 | 1.73ms | 2.54ms | 5.85ms | 0 |
| result (`/check/71f48dc9-51e7-4c1d-b79f-745e7ebbc966`) | 7665.41 | 1.44ms | 2.13ms | 2.90ms | 0 |
| health (`/api/health/status`) | 18254.77 | 1.07ms | 1.71ms | 2.39ms | 0 |
