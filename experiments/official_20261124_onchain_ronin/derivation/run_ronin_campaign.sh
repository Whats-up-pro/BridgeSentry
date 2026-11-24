#!/usr/bin/env bash
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO"
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
EXP="$REPO/experiments/official_20261124_onchain_ronin"
RUNS="$EXP/runs"
mkdir -p "$RUNS"
{
  echo "fixture=ronin_2024_onchain  fork_block=20468847  chain=ethereum(archive)"
  echo "binary_sha256=$(sha256sum $BIN | cut -d' ' -f1)  commit=$(git rev-parse HEAD)"
  echo "rustc=$(rustc --version 2>/dev/null)  date=$(date -u +%FT%TZ)"
  echo "spec=benchmarks/ronin_2024/official/spec_onchain.json"
} > "$EXP/run_info.txt"

for V in vulnerable patched; do
  for S in 1042 2042 3042; do
    OUT="$RUNS/$V"; mkdir -p "$OUT"
    BRIDGESENTRY_EVALUATION_MODE=official \
    BRIDGESENTRY_OFFICIAL_VARIANT=$V \
    BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
    BRIDGESENTRY_OFFICIAL_SEEDS=llm \
    BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
    "$BIN" --atg benchmarks/ronin_2024/llm_outputs/atg.json \
           --scenarios benchmarks/ronin_2024/llm_outputs/hypotheses.json \
           --metadata benchmarks/ronin_2024/metadata.json \
           --output "$OUT/seed_$S.json" --budget 75 --runs 1 --seed $S \
           --source-rpc "$ETH" --dest-rpc "$ETH" --source-block 20468847 --dest-block 20468847 \
           > "$OUT/seed_$S.log" 2>&1
    rc=$?
    ve=$(python3 -c "import json;print(json.load(open('$OUT/seed_$S.json')).get('valid_exploits'))" 2>/dev/null)
    echo "$V seed=$S rc=$rc valid_exploits=$ve"
  done
done
echo ALL_DONE
