#!/usr/bin/env bash
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --qos=mig2-35
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=logs/a1_%j.out
#SBATCH --error=logs/a1_%j.err
#
# A-1 (Core A): C1 FPR + C2 VER on the 7 on-chain fixtures, RANDOM seeds, 20
# seeds x {vulnerable, patched}, official oracle, CPU-only (no --gres) per the
# verified HPC facts (partition=normal, qos=mig2-35, MAX 8 cpu/job). Follows Huong_dan_HPC_
# dungtrt.pdf: login/prepare/submit only; many runs batched into ONE job via
# xargs -P; results copied back to the repo afterwards.
#
# Expects, under /datastore/dungtrt/bridgesentry/:
#   bin/bridgesentry-fuzzer  (musl static, commit 1149b42, sha256 d9cf542e...)
#   bin/solc                 (0.8.20 static)
#   repo/                    (BridgeSentry at commit 1149b42)
set -uo pipefail
BASE=/datastore/dungtrt/bridgesentry
export REPO="$BASE/repo"
export BIN="$BASE/bin/bridgesentry-fuzzer"
export PATH="$BASE/bin:/cm/local/apps/python3/bin:$PATH"   # solc + python3
cd "$REPO"

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$BASE/runs/a1_random_$STAMP/official_runs"
mkdir -p "$OUT" logs

# empty RPC (local-fixture execution, NOT a mainnet fork)
PORT=18610
python3 scripts/official/empty_rpc.py "$PORT" &
RPC_PID=$!
trap 'kill "$RPC_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do
  python3 - "$PORT" <<'PY' && break
import socket,sys
s=socket.socket(); s.settimeout(1)
try: s.connect(("127.0.0.1",int(sys.argv[1]))); print("rpc up"); sys.exit(0)
except Exception: sys.exit(1)
PY
  sleep 0.5
done
export RPC_URL="http://127.0.0.1:$PORT"

# jobs: 7 fixtures x {vulnerable,patched} x random x 20 seeds (1042..20042), 300s each
: > "$OUT/jobs.txt"
for b in nomad qubit polynetwork ronin_2024 crosscurve verus feg_bridge_2024; do
  for v in vulnerable patched; do
    for s in $(seq 1042 1000 20042); do
      echo "$b $v random $s 300 $OUT" >> "$OUT/jobs.txt"
    done
  done
done
echo "A-1: $(wc -l < "$OUT/jobs.txt") runs, 8 cpus, -P 7"

BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 xargs -P 7 -L1 scripts/official/run_official.sh < "$OUT/jobs.txt"
XRC=$?

python3 scripts/official/aggregate_official.py "$OUT"
echo "A-1 done (xargs rc=$XRC). Summary: $OUT/summary_official.csv"
