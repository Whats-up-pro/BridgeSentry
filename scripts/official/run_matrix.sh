#!/usr/bin/env bash
# run_matrix.sh <out_root> <budget_s> <parallel_jobs> <bench>...
#
# Runs {vulnerable, patched} x {llm, random} x $SEEDS for every bench, then
# writes <out_root>/summary_official.csv. Unless RPC_URL is already set, it
# starts empty_rpc.py on port 18545 (local-fixture execution, NOT a mainnet
# fork) and stops it on exit.
#   SEEDS   default "1042 2042 3042 4042 5042"
#   RPC_URL use an existing endpoint (e.g. a mainnet-fork node) instead
set -eu
OUT_ROOT=$1; BUDGET=$2; PAR=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
SEEDS=${SEEDS:-"1042 2042 3042 4042 5042"}
if [ -z "${RPC_URL:-}" ]; then
  python3 "$HERE/empty_rpc.py" 18545 &
  RPC_PID=$!
  trap 'kill "$RPC_PID" 2>/dev/null || true' EXIT
  export RPC_URL=http://127.0.0.1:18545
  sleep 1
fi
mkdir -p "$OUT_ROOT"
for b in "$@"; do
  for v in vulnerable patched; do
    for s in llm random; do
      for seed in $SEEDS; do
        echo "$b $v $s $seed $BUDGET $OUT_ROOT"
      done
    done
  done
done > "$OUT_ROOT/jobs.txt"
xargs -P "$PAR" -L1 "$HERE/run_official.sh" < "$OUT_ROOT/jobs.txt"
python3 "$HERE/aggregate_official.py" "$OUT_ROOT"
