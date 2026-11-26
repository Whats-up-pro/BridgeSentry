#!/usr/bin/env bash
# Fork robustness + unguided-baseline campaign on REAL Ronin mainnet bytecode.
# New frozen experiment dir; reads archive RPC at runtime from the env file
# (the URL carries an API key and is NEVER written to any file in the tree).
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"

REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
[ -n "$ETH" ] || { echo "FATAL: ETH_ARCHIVE_RPC empty"; exit 3; }

EXP="$REPO/experiments/official_20261126_onchain_fork_robustness"
RUNS="$EXP/runs"
mkdir -p "$RUNS"

BUDGET=75
SEEDS="1042 2042 3042 4042 5042 6042 7042 8042 9042 10042"   # n=10

{
  echo "campaign=onchain_fork_robustness"
  echo "fixture=ronin_2024_onchain  fork_block=20468847  chain=ethereum(archive)"
  echo "spec=benchmarks/ronin_2024/official/spec_onchain.json  budget_s=$BUDGET  n_seeds=10"
  echo "seeds=$SEEDS"
  echo "binary=$BIN"
  echo "binary_sha256=$(sha256sum $BIN | cut -d' ' -f1)"
  echo "commit=$(git rev-parse HEAD)"
  echo "rustc=$(rustc --version 2>/dev/null)"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "rpc=Ethereum mainnet archive (Alchemy); key read from env at runtime, NOT stored here"
  echo "hardware=developer workstation (WSL2) over residential link; TTVE is RPC-bound, reported to show termination not as a perf benchmark"
} > "$EXP/run_info.txt"

run_one () {   # <variant> <seedmode> <seed>
  local V=$1 SM=$2 S=$3
  local OUT="$RUNS/${V}_${SM}"; mkdir -p "$OUT"
  BRIDGESENTRY_EVALUATION_MODE=official \
  BRIDGESENTRY_OFFICIAL_VARIANT=$V \
  BRIDGESENTRY_OFFICIAL_SPEC=spec_onchain.json \
  BRIDGESENTRY_OFFICIAL_SEEDS=$SM \
  BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=0 \
  "$BIN" --atg benchmarks/ronin_2024/llm_outputs/atg.json \
         --scenarios benchmarks/ronin_2024/llm_outputs/hypotheses.json \
         --metadata benchmarks/ronin_2024/metadata.json \
         --output "$OUT/seed_$S.json" --budget "$BUDGET" --runs 1 --seed "$S" \
         --source-rpc "$ETH" --dest-rpc "$ETH" --source-block 20468847 --dest-block 20468847 \
         > "$OUT/seed_$S.log" 2>&1
  local rc=$?
  local ve="?" tt="?"
  if [ -s "$OUT/seed_$S.json" ]; then
    read ve tt < <(python3 -c "import json;d=json.load(open('$OUT/seed_$S.json'));print(d.get('valid_exploits'), d.get('first_valid_exploit_s'))" 2>/dev/null)
  fi
  echo "[$(date -u +%H:%M:%S)] $V/$SM seed=$S rc=$rc valid_exploits=$ve ttve=$tt"
}

echo "=== ARM 1: vulnerable x grounded(llm) x10 (expect robust reconstruction) ==="
for S in $SEEDS; do run_one vulnerable llm "$S"; done
echo "=== ARM 2: patched x grounded(llm) x10 (real fixed bytecode; expect 0/10) ==="
for S in $SEEDS; do run_one patched llm "$S"; done
echo "=== ARM 3: vulnerable x random(unguided) x10 (real fork is hard without guidance) ==="
for S in $SEEDS; do run_one vulnerable random "$S"; done

echo "=== TALLY ==="
python3 - "$RUNS" <<'PY'
import json,glob,os,sys
runs=sys.argv[1]
for arm in ["vulnerable_llm","patched_llm","vulnerable_random"]:
    fs=sorted(glob.glob(os.path.join(runs,arm,"seed_*.json")))
    ve=0; tt=[]
    for f in fs:
        try: d=json.load(open(f))
        except Exception: continue
        v=d.get("valid_exploits") or 0
        if v>0:
            ve+=1
            if d.get("first_valid_exploit_s") is not None: tt.append(d["first_valid_exploit_s"])
    import statistics
    med="n/a" if not tt else round(statistics.median(tt),4)
    print(f"  {arm:18s}: valid {ve}/{len(fs)}  median_ttve_s={med}")
PY
echo ALL_DONE
