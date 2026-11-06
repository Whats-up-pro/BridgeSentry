#!/usr/bin/env bash
# run_matrix.sh <out_root> <budget_s> <parallel_jobs> <bench>...
#
# Runs {vulnerable, patched} x {llm, random} x $SEEDS for every bench, then
# writes <out_root>/summary_official.csv. Unless RPC_URL is already set, it
# starts empty_rpc.py (local-fixture execution, NOT a mainnet fork) on
# $RPC_PORT, or on a free port when RPC_PORT is unset, waits until it answers,
# and stops it on exit.
#   SEEDS     default "1042 2042 3042 4042 5042"
#   RPC_URL   use an existing endpoint (e.g. a mainnet-fork node) instead
#   RPC_PORT  fixed port for the local empty RPC
#
# The `llm` seed row is emitted only for benchmarks that actually have LLM
# scenarios: a benchmark whose benchmarks/<b>/llm_outputs/hypotheses.json is
# absent, marked {"placeholder": true}, or has no scenarios runs `random` only.
#
# Exit status: 0 only if every run exited 0. Failed runs are recorded in
# seed_*.rc, excluded from outcome columns and counted in `runs_failed`.
set -eu
OUT_ROOT=$1; BUDGET=$2; PAR=$3; shift 3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${REPO:-$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null)}
[ -n "$REPO" ] || { echo "run_matrix.sh: set REPO (not a git checkout)" >&2; exit 2; }
SEEDS=${SEEDS:-"1042 2042 3042 4042 5042"}

# echoes "llm random" when real LLM scenarios exist for <bench>, else "random".
seed_modes_for() {
  local hyp="$REPO/benchmarks/$1/llm_outputs/hypotheses.json"
  if [ -f "$hyp" ] && python3 - "$hyp" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
scenarios = d.get("scenarios") or []
sys.exit(0 if (not d.get("placeholder") and len(scenarios) > 0) else 1)
PY
  then
    echo "llm random"
  else
    echo "random"
  fi
}

if [ -z "${RPC_URL:-}" ]; then
  PORT=${RPC_PORT:-$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')}
  python3 "$HERE/empty_rpc.py" "$PORT" &
  RPC_PID=$!
  trap 'kill "$RPC_PID" 2>/dev/null || true; wait "$RPC_PID" 2>/dev/null || true' EXIT
  export RPC_URL=http://127.0.0.1:$PORT
  if ! python3 - "$RPC_URL" <<'PY'
import json, sys, time, urllib.request
url = sys.argv[1]
body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}).encode()
for _ in range(100):
    try:
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
        if json.load(urllib.request.urlopen(req, timeout=1)).get("result"):
            sys.exit(0)
    except Exception:
        time.sleep(0.1)
sys.exit(1)
PY
  then
    echo "run_matrix.sh: empty RPC on $RPC_URL did not become ready" >&2
    exit 2
  fi
fi
mkdir -p "$OUT_ROOT"
for b in "$@"; do
  modes=$(seed_modes_for "$b")
  for v in vulnerable patched; do
    for s in $modes; do
      for seed in $SEEDS; do
        echo "$b $v $s $seed $BUDGET $OUT_ROOT"
      done
    done
  done
done > "$OUT_ROOT/jobs.txt"
set +e
xargs -P "$PAR" -L1 "$HERE/run_official.sh" < "$OUT_ROOT/jobs.txt"
XRC=$?
set -e
python3 "$HERE/aggregate_official.py" "$OUT_ROOT"
if [ "$XRC" -ne 0 ]; then
  echo "run_matrix.sh: at least one run failed (xargs status $XRC); see runs_failed in summary_official.csv" >&2
  exit 1
fi
