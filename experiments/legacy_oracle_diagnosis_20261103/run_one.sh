#!/usr/bin/env bash
# run_one.sh <cond> <bench_dir> <label> <seed> <budget>
# cond: syn  = no RPC (fuzzer falls back to scenario-only state)
#       real = dual-EVM with locally deployed fixture bytecode, legacy oracle
#       exec = same as real, but checker sees execution-derived state only
set -u
COND=$1; B=$2; LABEL=$3; SEED=$4; BUDGET=$5
REPO=/home/claude/whats-up-pro/bridgesentry
BIN=$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=$REPO/_exp/runs/$COND/$LABEL; mkdir -p "$OUT"
export PATH=/home/claude/tools:$PATH
BLOCK=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['fork']['block_number'])" "$B/metadata.json")
ARGS=(--atg "$B/llm_outputs/atg.json" --scenarios "$B/llm_outputs/hypotheses.json"
      --metadata "$B/metadata.json" --output "$OUT/seed_$SEED.json"
      --budget "$BUDGET" --runs 1 --seed "$SEED")
if [ "$COND" != syn ]; then
  ARGS+=(--source-rpc http://127.0.0.1:18545 --dest-rpc http://127.0.0.1:18545
         --source-block "$BLOCK" --dest-block "$BLOCK")
fi
if [ "$COND" = exec ]; then export BRIDGESENTRY_DIAG_EXEC_ONLY=1; fi
cd "$REPO"
"$BIN" "${ARGS[@]}" > "$OUT/seed_$SEED.log" 2>&1
echo "$COND $LABEL $SEED rc=$?"
