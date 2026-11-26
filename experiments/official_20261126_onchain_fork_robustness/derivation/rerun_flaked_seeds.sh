#!/usr/bin/env bash
# Re-run the two grounded seeds that hit a transient DNS fork-init failure.
# Accept a run ONLY if it genuinely forked (no "Dual-EVM init failed" fallback).
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
OUT="$REPO/experiments/official_20261126_onchain_fork_robustness/runs/vulnerable_llm"

for S in 3042 4042; do
  ok=0
  for attempt in 1 2 3 4 5; do
    rm -f "$OUT/seed_$S.json" "$OUT/seed_$S.log"
    BRIDGESENTRY_EVALUATION_MODE=official \
    BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable \
    BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
    BRIDGESENTRY_OFFICIAL_SEEDS=llm \
    BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
    "$BIN" --atg benchmarks/ronin_2024/llm_outputs/atg.json \
           --scenarios benchmarks/ronin_2024/llm_outputs/hypotheses.json \
           --metadata benchmarks/ronin_2024/metadata.json \
           --output "$OUT/seed_$S.json" --budget 75 --runs 1 --seed "$S" \
           --source-rpc "$ETH" --dest-rpc "$ETH" --source-block 20468847 --dest-block 20468847 \
           > "$OUT/seed_$S.log" 2>&1
    rc=$?
    if grep -q "Dual-EVM init failed\|Temporary failure in name resolution" "$OUT/seed_$S.log"; then
      echo "seed=$S attempt=$attempt: DNS/fork fallback, retrying..."; sleep 5; continue
    fi
    ve="?"; [ -s "$OUT/seed_$S.json" ] && ve=$(python3 -c "import json;print(json.load(open('$OUT/seed_$S.json')).get('valid_exploits'))" 2>/dev/null)
    tt="?"; [ -s "$OUT/seed_$S.json" ] && tt=$(python3 -c "import json;print(json.load(open('$OUT/seed_$S.json')).get('first_valid_exploit_s'))" 2>/dev/null)
    echo "seed=$S attempt=$attempt: CLEAN FORK rc=$rc valid_exploits=$ve ttve=$tt"
    ok=1; break
  done
  [ "$ok" = 1 ] || echo "seed=$S: FAILED to get a clean forked run after retries"
done
echo RERUN_DONE
