#!/usr/bin/env bash
# A3 benign hard-negative FPR campaign on the benign_bridge fixture (empty-RPC, local).
# 20 seeds x {random, llm} x 300s on the benign variant -> expect candidates 0/40 (FPR 0).
# Plus 2 unpaired llm runs that must show a +DstToken gain (value genuinely moves).
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
export REPO
export BIN=$REPO/src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=/mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad/benign_bridge_campaign
mkdir -p "$OUT"
BUDGET=300
PAR=6
SEEDS="1042 2042 3042 4042 5042 6042 7042 8042 9042 10042 11042 12042 13042 14042 15042 16042 17042 18042 19042 20042"

run_one () {   # $1=mode(random|llm)  $2=seed  $3=spec  $4=tag
  local MODE="$1" SEED="$2" SPEC="$3" TAG="$4"
  local PORT J LOG strict=0
  [ "$MODE" = llm ] && strict=1
  PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
  python3 scripts/official/empty_rpc.py "$PORT" >/dev/null 2>&1 & local RP=$!
  sleep 0.6
  J="$OUT/${TAG}_${MODE}_s${SEED}.json"; LOG="$OUT/${TAG}_${MODE}_s${SEED}.log"
  RPC_URL="http://127.0.0.1:$PORT" \
  BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable \
  BRIDGESENTRY_OFFICIAL_SEEDS="$MODE" BRIDGESENTRY_OFFICIAL_STRICT_SEEDS="$strict" \
  BRIDGESENTRY_OFFICIAL_SPEC="$SPEC" \
  "$BIN" --atg benchmarks/benign_bridge/llm_outputs/atg.json \
         --scenarios benchmarks/benign_bridge/llm_outputs/hypotheses.json \
         --metadata benchmarks/benign_bridge/metadata.json \
         --output "$J" --budget "$BUDGET" --runs 1 --seed "$SEED" \
         --source-rpc "http://127.0.0.1:$PORT" --dest-rpc "http://127.0.0.1:$PORT" \
         --source-block 21500000 --dest-block 21500000 > "$LOG" 2>&1
  kill $RP 2>/dev/null
  python3 -c "
import json
try:
  d=json.load(open('$J'))
  c=(d.get('candidates') or [])
  g=c[0].get('gain') if c else None
  print('$TAG $MODE s$SEED | candidates=%s valid=%s iters=%s gain=%s'%(d.get('candidates_total'),d.get('valid_exploits'),d.get('iterations'),g))
except Exception as e: print('$TAG $MODE s$SEED | NOJSON', e)
"
}
export -f run_one
export REPO BIN OUT BUDGET

echo "===== PAIRED FPR: random x20 + llm x20 (expect candidates 0/40) ====="
# build job list
JOBS="$OUT/jobs.txt"; : > "$JOBS"
for S in $SEEDS; do echo "random $S spec.json paired" >> "$JOBS"; echo "llm $S spec.json paired" >> "$JOBS"; done
cat "$JOBS" | xargs -P "$PAR" -L1 bash -c 'run_one "$0" "$1" "$2" "$3"'

echo "===== UNPAIRED proof: llm x2 (expect +DstToken gain) ====="
for S in 1042 2042; do run_one llm "$S" spec_unpaired.json unpaired; done

echo "===== SUMMARY ====="
python3 - <<'PY'
import json,glob,os
OUT=os.environ['OUT']
paired=sorted(glob.glob(OUT+'/paired_*_s*.json'))
unp=sorted(glob.glob(OUT+'/unpaired_*_s*.json'))
def ct(f):
  try: return json.load(open(f)).get('candidates_total')
  except: return 'ERR'
pv=[ct(f) for f in paired]
print('paired runs:',len(paired),'| candidates totals:',sorted(set(pv)),'| n_with_candidate>0:',sum(1 for x in pv if isinstance(x,int) and x>0))
print('UNPAIRED:')
for f in unp:
  d=json.load(open(f)); c=(d.get('candidates') or [])
  print(' ',os.path.basename(f),'candidates=',d.get('candidates_total'),'gain=',c[0].get('gain') if c else None)
PY
echo CAMPAIGN_DONE
