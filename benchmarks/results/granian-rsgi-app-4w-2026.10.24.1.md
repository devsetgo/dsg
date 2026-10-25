# Benchmark: granian-rsgi-app-4w-2026.10.24.1

- date: 2026-10-25T00:01:23+00:00
- host: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64, 20 CPUs
- wrk2: -t4 -c64 -d20s; saturation -R20000, latency -R300

| endpoint | max req/s | p50 @300/s | p90 @300/s | p99 @300/s | errors |
|---|---|---|---|---|---|
| form (`/check`) | 7035.86 | 1.67ms | 2.43ms | 4.13ms | 0 |
| result (`/check/9fa1dac2-60be-4511-a95a-205271568609`) | 11014.41 | 1.49ms | 2.10ms | 2.65ms | 0 |
| health (`/api/health/status`) | 19962.22 | 1.06ms | 1.53ms | 2.02ms | 0 |
