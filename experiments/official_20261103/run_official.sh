#!/usr/bin/env bash
# run_official.sh <bench> <variant> <seeds:llm|random> <seed> <budget>
set -u
B=$1; V=$2; S=$3; SEED=$4; BUDGET=$5
REPO=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)
BIN=$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=$REPO/_exp/official_runs/$B/$V/$S; mkdir -p "$OUT"
# solc 0.8.20 must be on PATH
META=$REPO/benchmarks/$B/metadata.json
SRC_BLOCK=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['fork']['block_number'])" "$META")
DST_BLOCK=$(python3 -c "import json,sys;f=json.load(open(sys.argv[1]))['fork'];print(f.get('dest_block_number',f['block_number']))" "$META")
cd "$REPO"
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=$V BRIDGESENTRY_OFFICIAL_SEEDS=$S \
"$BIN" --atg benchmarks/$B/llm_outputs/atg.json --scenarios benchmarks/$B/llm_outputs/hypotheses.json \
  --metadata "$META" --output "$OUT/seed_$SEED.json" --budget "$BUDGET" --runs 1 --seed "$SEED" \
  --source-rpc http://127.0.0.1:18545 --dest-rpc http://127.0.0.1:18545 --source-block "$SRC_BLOCK" --dest-block "$DST_BLOCK" \
  > "$OUT/seed_$SEED.log" 2>&1
echo "$B $V $S $SEED rc=$?"
