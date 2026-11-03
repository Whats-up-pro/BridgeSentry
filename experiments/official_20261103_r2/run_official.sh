#!/usr/bin/env bash
# run_official.sh <bench> <variant> <seeds:llm|random> <seed> <budget>
# Local fixture execution against an EMPTY JSON-RPC (empty_rpc.py), NOT a mainnet fork.
set -u
B=$1; V=$2; S=$3; SEED=$4; BUDGET=$5
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(git -C "$HERE" rev-parse --show-toplevel)
BIN=$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer
RPC=${RPC:-http://127.0.0.1:18545}
OUT=$HERE/official_runs/$B/$V/$S; mkdir -p "$OUT"
META=$REPO/benchmarks/$B/metadata.json
# Fork block numbers come from metadata.json (fork.block_number; optional
# fork.dest_block_number). With the empty RPC they only label the block env.
SRC_BLOCK=$(python3 -c "import json,sys;m=json.load(open(sys.argv[1]));print(m['fork']['block_number'])" "$META")
DST_BLOCK=$(python3 -c "import json,sys;m=json.load(open(sys.argv[1]));f=m['fork'];print(f.get('dest_block_number',f['block_number']))" "$META")
cd "$REPO"
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=$V BRIDGESENTRY_OFFICIAL_SEEDS=$S \
"$BIN" --atg benchmarks/$B/llm_outputs/atg.json --scenarios benchmarks/$B/llm_outputs/hypotheses.json \
  --metadata "$META" --output "$OUT/seed_$SEED.json" --budget "$BUDGET" --runs 1 --seed "$SEED" \
  --source-rpc "$RPC" --dest-rpc "$RPC" --source-block "$SRC_BLOCK" --dest-block "$DST_BLOCK" \
  > "$OUT/seed_$SEED.log" 2>&1
echo "$B $V $S $SEED rc=$?"
