#!/usr/bin/env bash
# run_official.sh <bench> <variant:vulnerable|patched> <seeds:llm|random> <seed> <budget_s> [out_root]
#
# Runs one official-oracle fuzzing job (BRIDGESENTRY_EVALUATION_MODE=official).
# Requires: the release fuzzer build, solc 0.8.20 on PATH, and a JSON-RPC
# endpoint at $RPC_URL (default http://127.0.0.1:18545), e.g. empty_rpc.py.
# With empty_rpc.py this is local-fixture execution, NOT a mainnet fork.
set -u
B=$1; V=$2; S=$3; SEED=$4; BUDGET=$5
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
OUT_ROOT=${6:-$REPO/_exp/official_runs}
RPC_URL=${RPC_URL:-http://127.0.0.1:18545}
BIN=${BIN:-$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer}
META=$REPO/benchmarks/$B/metadata.json
SRC_BLOCK=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["fork"]["block_number"])' "$META")
DST_BLOCK=$(python3 -c 'import json,sys; f=json.load(open(sys.argv[1]))["fork"]; print(f.get("dest_block_number", f["block_number"]))' "$META")
OUT=$OUT_ROOT/$B/$V/$S
mkdir -p "$OUT"
cd "$REPO"
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=$V BRIDGESENTRY_OFFICIAL_SEEDS=$S \
"$BIN" --atg "benchmarks/$B/llm_outputs/atg.json" --scenarios "benchmarks/$B/llm_outputs/hypotheses.json" \
  --metadata "$META" --output "$OUT/seed_$SEED.json" --budget "$BUDGET" --runs 1 --seed "$SEED" \
  --source-rpc "$RPC_URL" --dest-rpc "$RPC_URL" --source-block "$SRC_BLOCK" --dest-block "$DST_BLOCK" \
  > "$OUT/seed_$SEED.log" 2>&1
echo "$B $V $S $SEED rc=$?"
