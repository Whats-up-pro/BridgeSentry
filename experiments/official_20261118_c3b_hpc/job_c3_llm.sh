#!/usr/bin/env bash
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --qos=mig2-35
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=07:00:00
#SBATCH --output=logs/c3_%j.out
#SBATCH --error=logs/c3_%j.err
#
# C3 (leakage-aware holdout): official oracle with gpt-oss-120b seeds (via
# OpenRouter; retrieval all-MiniLM-L6-v2 + FAISS over the audited 50-record KB)
# under 4 KB regimes {known, exact, temporal, no_rag}, on the 4 fixtures dated
# after the model's stated cutoff (ronin_2024, crosscurve, verus, feg_bridge_2024)
# plus PolyNetwork (2021, before the cutoff) as the contamination contrast.
# 5 fixtures x 4 regimes x 20 seeds = 400 runs per variant, 300 s each -- the
# same seed numbers, budget and fuzzer binary as A-1, whose random-seed runs are
# the baseline (official_20261114_a1_hpc).
#
# Usage, from the C3 repo copy on /datastore (logs/ must exist there):
#   sbatch --export=ALL,REPO=$PWD scripts/official/job_c3_llm.sh vulnerable
#   sbatch --export=ALL,REPO=$PWD scripts/official/job_c3_llm.sh patched
# SEED_ALIAS selects the seed sets under llm_outputs/<alias>/<regime>/:
# gpt-oss-or (C3, default) or gpt-oss-or-grounded (C3b, docs/C3b_protocol.md), e.g.
#   sbatch --export=ALL,REPO=$PWD,SEED_ALIAS=gpt-oss-or-grounded scripts/official/job_c3_llm.sh vulnerable
#
# CPU-only (no --gres), partition=normal, qos=mig2-35 (max 8 cpu/job); many runs
# batched into ONE job via xargs -P, per Huong_dan_HPC_dungtrt.pdf. Results are
# copied back to the repo afterwards.
set -uo pipefail
VARIANT=${1:?usage: job_c3_llm.sh <vulnerable|patched>}
case "$VARIANT" in vulnerable|patched) ;; *) echo "bad variant $VARIANT" >&2; exit 2 ;; esac
BASE=/datastore/dungtrt/bridgesentry
export REPO=${REPO:?set REPO to the C3 repo copy}
export BIN="$BASE/bin/bridgesentry-fuzzer"
export PATH="$BASE/bin:/cm/local/apps/python3/bin:$PATH"   # solc + python3
cd "$REPO"

SEED_ALIAS=${SEED_ALIAS:-gpt-oss-or}   # gpt-oss-or (C3) or gpt-oss-or-grounded (C3b)
case "$SEED_ALIAS" in gpt-oss-or) RUN_PREFIX=c3_llm ;; *) RUN_PREFIX="c3_$SEED_ALIAS" ;; esac
STAMP=$(date +%Y%m%d_%H%M%S)
RUN="$BASE/runs/${RUN_PREFIX}_${VARIANT}_$STAMP"
mkdir -p "$RUN" logs
{
  echo "job=${SLURM_JOB_ID:-none} variant=$VARIANT seed_alias=$SEED_ALIAS repo=$REPO commit=$(cat "$REPO/COMMIT" 2>/dev/null || echo unknown)"
  echo "node=$(hostname) start=$(date -u +%FT%TZ)"
  sha256sum "$BIN"
} > "$RUN/run_info.txt"

# empty RPC (local-fixture execution, NOT a mainnet fork) on a free port, so
# concurrent jobs on the same node never share (or outlive) an RPC server
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
python3 scripts/official/empty_rpc.py "$PORT" &
RPC_PID=$!
trap 'kill "$RPC_PID" 2>/dev/null || true' EXIT
for _ in $(seq 1 60); do
  kill -0 "$RPC_PID" 2>/dev/null || { echo "empty_rpc died (port $PORT)" >&2; exit 3; }
  python3 - "$PORT" <<'PY' && break
import socket,sys
s=socket.socket(); s.settimeout(1)
try: s.connect(("127.0.0.1",int(sys.argv[1]))); print("rpc up"); sys.exit(0)
except Exception: sys.exit(1)
PY
  sleep 0.5
done
export RPC_URL="http://127.0.0.1:$PORT"

# jobs: 4 regimes x 5 fixtures x 20 seeds (1042..20042), 300 s; regime-major so
# a regime's runs finish together. One out_root per regime (all are `llm`).
#
# Seed staging: the fuzzer takes the benchmark directory to be the parent of the
# directory that holds atg.json (contract_loader.rs), so a seed set must sit
# exactly one level below benchmarks/<b>/. Each set is copied there under a
# per-job name; the copies are checked byte-identical (cmp) and their sha256 is
# logged in $RUN/seed_staging.sha256, with each set's provenance in
# $RUN/seed_provenance/.
TAG="seed_${SEED_ALIAS}_${SLURM_JOB_ID:-local}"
# remove this job's staged seed copies on exit (the staged files are logged above)
trap 'kill "$RPC_PID" 2>/dev/null || true; rm -rf "$REPO"/benchmarks/*/".${TAG}_"*' EXIT
: > "$RUN/jobs.txt"
: > "$RUN/seed_staging.sha256"
mkdir -p "$RUN/seed_provenance"
for r in known exact temporal no_rag; do
  for b in ronin_2024 crosscurve verus feg_bridge_2024 polynetwork; do
    src="$REPO/benchmarks/$b/official/llm_outputs/$SEED_ALIAS/$r"
    { test -s "$src/hypotheses.json" && test -s "$src/atg.json"; } || { echo "missing seeds $src" >&2; exit 4; }
    sd="$REPO/benchmarks/$b/.${TAG}_$r"
    mkdir -p "$sd"
    cp "$src/atg.json" "$src/hypotheses.json" "$sd/"
    { cmp -s "$src/atg.json" "$sd/atg.json" && cmp -s "$src/hypotheses.json" "$sd/hypotheses.json"; } \
      || { echo "staged copy differs: $sd" >&2; exit 5; }
    (cd "$REPO" && sha256sum "${src#"$REPO"/}/atg.json" "${src#"$REPO"/}/hypotheses.json") >> "$RUN/seed_staging.sha256"
    cp "$src/provenance.json" "$RUN/seed_provenance/${b}_${r}.json"
    for s in $(seq 1042 1000 20042); do
      echo "$b $VARIANT llm $s 300 $RUN/$r/official_runs $sd" >> "$RUN/jobs.txt"
    done
  done
done
echo "C3 $VARIANT: $(wc -l < "$RUN/jobs.txt") runs, 8 cpus, -P 7, rpc :$PORT"

BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1 xargs -P 7 -L1 scripts/official/run_official.sh < "$RUN/jobs.txt"
XRC=$?

for r in known exact temporal no_rag; do
  python3 scripts/official/aggregate_official.py "$RUN/$r/official_runs"
done
echo "end=$(date -u +%FT%TZ) xargs_rc=$XRC" >> "$RUN/run_info.txt"
echo "C3 $VARIANT done (xargs rc=$XRC). Summaries: $RUN/<regime>/official_runs/summary_official.csv"
