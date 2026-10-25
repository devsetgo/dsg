# Benchmark: granian-rsgi-4w-dsglib-2026.10.24.1

- date: 2026-10-24T23:41:49+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 6991.35 | 1.58ms | 2.35ms | 3.56ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 13204.81 | 1.35ms | 2.03ms | 3.19ms | 0 |
| health (`/api/health/status`) | 19962.27 | 1.04ms | 1.61ms | 2.13ms | 0 |
