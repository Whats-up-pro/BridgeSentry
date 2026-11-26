#!/usr/bin/env bash
# Nomad fork robustness + unguided-baseline campaign on REAL mainnet bytecode.
# Fork guard baked in: any synthetic-fallback (DNS/RPC flake) is retried, never counted.
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
[ -n "$ETH" ] || { echo "FATAL: ETH_ARCHIVE_RPC empty"; exit 3; }

EXP="$REPO/experiments/official_20261126_onchain_fork_robustness/nomad"
RUNS="$EXP/runs"
mkdir -p "$RUNS"
BUDGET=75
BLOCK=15259100
SEEDS="1042 2042 3042 4042 5042 6042 7042 8042 9042 10042"

{
  echo "campaign=onchain_fork_robustness  fixture=nomad_onchain"
  echo "fork_block=$BLOCK  chain=ethereum(archive)  budget_s=$BUDGET  n_seeds=10"
  echo "spec=benchmarks/nomad/official/spec_onchain.json"
  echo "binary=$BIN  binary_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "commit=$(git rev-parse HEAD)  rustc=$(rustc --version 2>/dev/null)  date_utc=$(date -u +%FT%TZ)"
  echo "rpc=Ethereum mainnet archive (Alchemy); key read from env at runtime, NOT stored"
  echo "note=fork guard retries any synthetic fallback; only genuinely-forked runs recorded"
} > "$EXP/run_info.txt"

run_guarded () {   # <variant> <seedmode> <seed>
  local V=$1 SM=$2 S=$3
  local OUT="$RUNS/${V}_${SM}"; mkdir -p "$OUT"
  local attempt ok=0
  for attempt in 1 2 3 4 5; do
    rm -f "$OUT/seed_$S.json" "$OUT/seed_$S.log"
    BRIDGESENTRY_EVALUATION_MODE=official \
    BRIDGESENTRY_OFFICIAL_VARIANT=$V \
    BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
    BRIDGESENTRY_OFFICIAL_SEEDS=$SM \
    BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
    "$BIN" --atg benchmarks/nomad/llm_outputs/atg.json \
           --scenarios benchmarks/nomad/llm_outputs/hypotheses.json \
           --metadata benchmarks/nomad/metadata.json \
           --output "$OUT/seed_$S.json" --budget "$BUDGET" --runs 1 --seed "$S" \
           --source-rpc "$ETH" --dest-rpc "$ETH" --source-block "$BLOCK" --dest-block "$BLOCK" \
           > "$OUT/seed_$S.log" 2>&1
    if grep -q "Dual-EVM init failed\|Temporary failure in name resolution" "$OUT/seed_$S.log"; then
      echo "[$(date -u +%H:%M:%S)] $V/$SM seed=$S attempt=$attempt: fork fallback, retry"; sleep 5; continue
    fi
    local ve="?" tt="?"
    [ -s "$OUT/seed_$S.json" ] && read ve tt < <(python3 -c "import json;d=json.load(open('$OUT/seed_$S.json'));print(d.get('valid_exploits'), d.get('first_valid_exploit_s'))" 2>/dev/null)
    echo "[$(date -u +%H:%M:%S)] $V/$SM seed=$S attempt=$attempt CLEAN valid_exploits=$ve ttve=$tt"
    ok=1; break
  done
  [ "$ok" = 1 ] || echo "[$(date -u +%H:%M:%S)] $V/$SM seed=$S: FAILED clean fork after retries"
}

echo "=== ARM 1: vulnerable x grounded(llm) x10 ==="
for S in $SEEDS; do run_guarded vulnerable llm "$S"; done
echo "=== ARM 2: patched x grounded(llm) x10 (real modeled fix; expect 0/10) ==="
for S in $SEEDS; do run_guarded patched llm "$S"; done
echo "=== ARM 3: vulnerable x random(unguided) x10 ==="
for S in $SEEDS; do run_guarded vulnerable random "$S"; done
echo ALL_DONE
