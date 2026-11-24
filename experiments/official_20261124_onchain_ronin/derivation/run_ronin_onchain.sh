#!/usr/bin/env bash
# usage: run_ronin_onchain.sh <vulnerable|patched> <budget_s>
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
V=${1:?variant}; BUDGET=${2:-120}
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
cd /mnt/d/HK1_2026-2027/NT505/BridgeSentry
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=/mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad
BRIDGESENTRY_EVALUATION_MODE=official \
BRIDGESENTRY_OFFICIAL_VARIANT=$V \
BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
BRIDGESENTRY_OFFICIAL_SEEDS=llm \
BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
"$BIN" --atg benchmarks/ronin_2024/llm_outputs/atg.json \
       --scenarios benchmarks/ronin_2024/llm_outputs/hypotheses.json \
       --metadata benchmarks/ronin_2024/metadata.json \
       --output "$OUT/ronin_${V}.json" --budget "$BUDGET" --runs 1 --seed 1042 \
       --source-rpc "$ETH" --dest-rpc "$ETH" --source-block 20468847 --dest-block 20468847 \
       > "$OUT/ronin_${V}.log" 2>&1
echo "$V rc=$?  (budget ${BUDGET}s)"
echo "--- tail log ---"; tail -6 "$OUT/ronin_${V}.log"
if [ -s "$OUT/ronin_${V}.json" ]; then
  echo "--- report summary ---"
  python3 - "$OUT/ronin_${V}.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("variant:",d.get("variant"),"| candidates_total:",d.get("candidates_total"),"| valid_exploits:",d.get("valid_exploits"))
cands=d.get("candidates") or []
if cands:
    c=cands[0]
    print(" first candidate gates:",c.get("gates"))
    print(" gain:",c.get("gain"),"| entrypoints:",c.get("gain_entrypoints"))
    print(" patched_control:",c.get("patched_control"))
PY
else
  echo "(no report json written)"
fi
