#!/usr/bin/env bash
# Qubit dual-chain on-chain fork reconstruction (3rd external-validity incident).
# ETH source (QBridge deposit, 0-value, address(0) token) -> faithful relay ->
# BSC dest (voteProposal -> qXETH mint). Patched = contractWhitelist[address(0)]->false.
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
BSC=$(grep -E "^BSC_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
[ -n "$ETH" ] && [ -n "$BSC" ] || { echo "FATAL: rpc empty"; exit 3; }
EXP="$REPO/experiments/official_20261126_onchain_qubit"
RUNS="$EXP/runs"; mkdir -p "$RUNS"
SBLK=14090169; DBLK=14738000; BUDGET=90; SEEDS="1042 2042 3042"

{
  echo "campaign=onchain_qubit_dualchain  fixture=qubit_2022_onchain"
  echo "source=Ethereum archive @ block $SBLK (QBridge 0x20E5E35b, handler 0x17B7163c)"
  echo "dest=BSC archive @ block $DBLK (QBridge 0x4d8aE68f, qXETH 0xfd7a5506)"
  echo "spec=benchmarks/qubit/official/spec_onchain.json  budget_s=$BUDGET  n_seeds=3"
  echo "binary=$BIN  binary_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "commit=$(git rev-parse HEAD)  rustc=$(rustc --version 2>/dev/null)  date_utc=$(date -u +%FT%TZ)"
  echo "rpc=ETH+BSC mainnet archive (Alchemy); keys read from env at runtime, NOT stored"
  echo "relayer-registration=grantRole(RELAYER_ROLE, harness relayer) from admin 0xbeE39712 in setup (modeled faithful relay)"
  echo "patch=contractWhitelist[address(0)] slot 105 -> 0 (handler proxy 0x17B7163c)"
} > "$EXP/run_info.txt"

run_guarded () {   # <variant> <seed>
  local V="$1"; local S="$2"
  local OUT="$RUNS/$V"; mkdir -p "$OUT"
  local attempt
  for attempt in 1 2 3 4 5; do
    rm -f "$OUT/seed_$S.json" "$OUT/seed_$S.log"
    BRIDGESENTRY_EVALUATION_MODE=official \
    BRIDGESENTRY_OFFICIAL_VARIANT=$V \
    BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
    BRIDGESENTRY_OFFICIAL_SEEDS=llm \
    BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
    "$BIN" --atg benchmarks/qubit/llm_outputs/atg.json \
           --scenarios benchmarks/qubit/llm_outputs/hypotheses.json \
           --metadata benchmarks/qubit/metadata.json \
           --output "$OUT/seed_$S.json" --budget "$BUDGET" --runs 1 --seed "$S" \
           --source-rpc "$ETH" --dest-rpc "$BSC" --source-block "$SBLK" --dest-block "$DBLK" \
           > "$OUT/seed_$S.log" 2>&1
    if grep -q "Dual-EVM init failed\|Temporary failure in name resolution" "$OUT/seed_$S.log"; then
      echo "[$(date -u +%H:%M:%S)] $V seed=$S attempt=$attempt: fork fallback, retry"; sleep 5; continue
    fi
    local ve="?"; [ -s "$OUT/seed_$S.json" ] && ve=$(python3 -c "import json;print(json.load(open('$OUT/seed_$S.json')).get('valid_exploits'))" 2>/dev/null)
    echo "[$(date -u +%H:%M:%S)] $V seed=$S attempt=$attempt CLEAN valid_exploits=$ve"
    break
  done
}

echo "=== VULNERABLE x3 (expect 3/3 valid, 7 gates, 190 qXETH) ==="
for S in $SEEDS; do run_guarded vulnerable "$S"; done
echo "=== PATCHED x3 (expect 0/3; whitelist flip reverts deposit) ==="
for S in $SEEDS; do run_guarded patched "$S"; done

echo "=== TALLY ==="
python3 - "$RUNS" <<'PY'
import json,glob,os,sys
runs=sys.argv[1]
for v in ["vulnerable","patched"]:
    fs=sorted(glob.glob(os.path.join(runs,v,"seed_*.json")))
    nv=0
    for f in fs:
        try: d=json.load(open(f))
        except Exception: continue
        if (d.get("valid_exploits") or 0)>0: nv+=1
    print(f"  {v}: valid {nv}/{len(fs)}")
PY
echo ALL_DONE
