#!/usr/bin/env bash
# run_official.sh <bench> <variant> <seeds:llm|random> <seed> <budget>
set -u
B=$1; V=$2; S=$3; SEED=$4; BUDGET=$5
REPO=/home/claude/whats-up-pro/bridgesentry
BIN=$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=$REPO/_exp/official_runs/$B/$V/$S; mkdir -p "$OUT"
export PATH=/home/claude/tools:$PATH
cd "$REPO"
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=$V BRIDGESENTRY_OFFICIAL_SEEDS=$S \
"$BIN" --atg benchmarks/$B/llm_outputs/atg.json --scenarios benchmarks/$B/llm_outputs/hypotheses.json \
  --metadata benchmarks/$B/metadata.json --output "$OUT/seed_$SEED.json" --budget "$BUDGET" --runs 1 --seed "$SEED" \
  --source-rpc http://127.0.0.1:18545 --dest-rpc http://127.0.0.1:18545 --source-block 15259100 --dest-block 15259100 \
  > "$OUT/seed_$SEED.log" 2>&1
echo "$B $V $S $SEED rc=$?"
