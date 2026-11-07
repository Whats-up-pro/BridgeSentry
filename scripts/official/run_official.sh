#!/usr/bin/env bash
# run_official.sh <bench> <variant:vulnerable|patched> <seeds:llm|random> <seed> <budget_s> [out_root]
#
# Runs one official-oracle fuzzing job (BRIDGESENTRY_EVALUATION_MODE=official).
# Requires: the release fuzzer build, solc 0.8.20 on PATH, and a JSON-RPC
# endpoint at $RPC_URL (default http://127.0.0.1:18545), e.g. empty_rpc.py.
# With empty_rpc.py this is local-fixture execution, NOT a mainnet fork.
#
# Exit status is the fuzzer's exit status; a run that exits 0 without writing
# its result JSON exits 97. The status is also written to seed_<n>.rc so the
# aggregator can tell an execution failure from a completed run without a
# valid exploit. Seeds run in strict mode (BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1):
# a requested `llm` run whose scenarios do not map to fixture calls fails
# instead of silently running random seeds. Set BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0
# only to reproduce pre-2026-11-05 behaviour.
set -u
B=$1; V=$2; S=$3; SEED=$4; BUDGET=$5
REPO=${REPO:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)}
[ -n "$REPO" ] || { echo "run_official.sh: set REPO (not a git checkout)" >&2; exit 2; }
OUT_ROOT=${6:-$REPO/_exp/official_runs}
RPC_URL=${RPC_URL:-http://127.0.0.1:18545}
BIN=${BIN:-$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer}
META=$REPO/benchmarks/$B/metadata.json
# SEED_DIR: directory holding atg.json + hypotheses.json for this run.
# Defaults to the legacy per-bench path; a campaign overrides it with a
# generated set, e.g. benchmarks/$B/official/llm_outputs/<model>/<regime>.
SEED_DIR=${SEED_DIR:-$REPO/benchmarks/$B/llm_outputs}
SRC_BLOCK=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fork"]["block_number"])' "$META")
DST_BLOCK=$(python3 -c 'import json,sys; f=json.load(open(sys.argv[1]))["fork"]; print(f.get("dest_block_number", f["block_number"]))' "$META")
OUT=$OUT_ROOT/$B/$V/$S
mkdir -p "$OUT"
rm -f "$OUT/seed_$SEED.json" "$OUT/seed_$SEED.rc"
cd "$REPO"
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=$V BRIDGESENTRY_OFFICIAL_SEEDS=$S \
BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=${BRIDGESENTRY_OFFICIAL_STRICT_SEEDS:-1} \
"$BIN" --atg "$SEED_DIR/atg.json" --scenarios "$SEED_DIR/hypotheses.json" \
  --metadata "$META" --output "$OUT/seed_$SEED.json" --budget "$BUDGET" --runs 1 --seed "$SEED" \
  --source-rpc "$RPC_URL" --dest-rpc "$RPC_URL" --source-block "$SRC_BLOCK" --dest-block "$DST_BLOCK" \
  > "$OUT/seed_$SEED.log" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ ! -s "$OUT/seed_$SEED.json" ]; then
  echo "run_official.sh: fuzzer exited 0 but wrote no result JSON" >> "$OUT/seed_$SEED.log"
  rc=97
fi
echo "$rc" > "$OUT/seed_$SEED.rc"
echo "$B $V $S $SEED rc=$rc"
exit "$rc"
