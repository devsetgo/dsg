#!/usr/bin/env bash
# Benchmark the local (non-PyPI) endpoints with wrk2.
#
# Usage: benchmarks/run.sh <label> <base_url> <form_path> <result_path> <health_path>
#   e.g. benchmarks/run.sh robyn http://localhost:5000 /check /check/<id> /api/health/status
#
# wrk2 is open-loop: -R fixes the offered request rate and latency is corrected for
# coordinated omission. RATE is set far above what either stack can serve, so
# "Requests/sec" is the saturated throughput and the latency percentiles show queueing.
set -euo pipefail

LABEL=$1 BASE=$2 FORM=$3 RESULT=$4 HEALTH=$5
WRK=${WRK:-$HOME/wrk2/wrk}
THREADS=${THREADS:-4} CONNS=${CONNS:-64} DURATION=${DURATION:-20s} RATE=${RATE:-50000}
# Fixed offered rate below both stacks' capacity, for a like-for-like latency comparison.
LAT_RATE=${LAT_RATE:-300}
OUT="$(dirname "$0")/results/${LABEL}.md"

{
  echo "# Benchmark: ${LABEL}"
  echo
  echo "- date: $(date -Iseconds)"
  echo "- host: $(uname -srm), $(nproc) CPUs"
  echo "- wrk2: -t${THREADS} -c${CONNS} -d${DURATION}; saturation -R${RATE}, latency -R${LAT_RATE}"
  echo
  echo "| endpoint | max req/s | p50 @${LAT_RATE}/s | p90 @${LAT_RATE}/s | p99 @${LAT_RATE}/s | errors |"
  echo "|---|---|---|---|---|---|"
} > "$OUT"

# wrk2 (2019) occasionally aborts with an hdr_histogram assertion, about 1 run in 8,
# even against a trivial server; it is the tool, not the app. Retry such a run.
wrk() {
  local out attempt
  for attempt in 1 2 3 4 5; do
    out=$("$WRK" "$@" 2>&1) && { printf '%s\n' "$out"; return 0; }
    grep -q Assertion <<< "$out" || { printf '%s\n' "$out"; return 1; }
  done
  printf '%s\n' "$out"; return 1
}

for name_path in "form:${FORM}" "result:${RESULT}" "health:${HEALTH}"; do
  name=${name_path%%:*} path=${name_path#*:}
  # warm up so every worker has compiled templates / opened its DB connection
  wrk -t2 -c16 -d5s -R1000 "${BASE}${path}" > /dev/null
  raw=$(wrk -t"$THREADS" -c"$CONNS" -d"$DURATION" -R"$RATE" --latency "${BASE}${path}")
  rps=$(awk '/Requests\/sec/ {print $2}' <<< "$raw")
  errs=$(awk '/Non-2xx|Socket errors/ {printf "%s ", $0}' <<< "$raw")
  raw=$(wrk -t"$THREADS" -c"$CONNS" -d"$DURATION" -R"$LAT_RATE" --latency "${BASE}${path}")
  p50=$(awk '$1=="50.000%" {print $2}' <<< "$raw")
  p90=$(awk '$1=="90.000%" {print $2}' <<< "$raw")
  p99=$(awk '$1=="99.000%" {print $2}' <<< "$raw")
  echo "| ${name} (\`${path}\`) | ${rps} | ${p50} | ${p90} | ${p99} | ${errs:-0} |" >> "$OUT"
done

cat "$OUT"
