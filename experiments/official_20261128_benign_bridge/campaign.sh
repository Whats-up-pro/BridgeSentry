#!/usr/bin/env bash
# A3 benign FPR campaign, re-run with the cluster build: fuzzer d9cf542 (musl static,
# same binary as A-1/C3/C3b/DeepSeek/A5) + solc 0.8.20 (sha256 0479d44f...), commit 9c21535.
# Same design as the cluster job 182954: 20 random + 20 llm on benign_bridge (vulnerable),
# 2 llm on the unpaired staging copy; 300 s; xargs -P 7; one shared empty RPC.
set -u
export PATH=/root/.local/solc0820:$PATH
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
SC=/mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad
export BIN=$SC/hpcbin/bridgesentry-fuzzer
E=$REPO/experiments/official_20261128_benign_bridge
mkdir -p "$E/runs"
cd "$REPO" || exit 2
# unpaired staging copy OUTSIDE the repo (so the tracked fixture set is unchanged)
STAGE=/root/benign_stage/benchmarks
rm -rf /root/benign_stage; mkdir -p "$STAGE"
cp -r benchmarks/_official_common "$STAGE/"
cp -r benchmarks/benign_bridge "$STAGE/benign_bridge_unpaired"
cp benchmarks/benign_bridge/official/spec_unpaired.json "$STAGE/benign_bridge_unpaired/official/spec.json"
rm -f "$STAGE/benign_bridge_unpaired/official/spec_unpaired.json"
{
  echo "commit $(git rev-parse HEAD)  (fixture benchmarks/benign_bridge unchanged since f51223d)"
  echo "fuzzer: cluster build"; sha256sum "$BIN"
  echo "solc:"; sha256sum "$(readlink -f "$(command -v solc)")"; solc --version | tail -1
  echo "unpaired staging spec (= official/spec_unpaired.json):"
  sha256sum "$STAGE/benign_bridge_unpaired/official/spec.json" benchmarks/benign_bridge/official/spec_unpaired.json
  echo "host: developer workstation (WSL2), $(nproc) vCPU, $(uname -sr); xargs -P 7; empty RPC (not a mainnet fork)"
  date -u +"started %Y-%m-%dT%H:%M:%SZ"
} > "$E/run_info.txt"
PORT=18631
python3 scripts/official/empty_rpc.py "$PORT" >/dev/null 2>&1 & RP=$!
trap 'kill $RP 2>/dev/null' EXIT
sleep 1
export RPC=http://127.0.0.1:$PORT E

one () {  # bench_root bench mode seed tag
  local ROOT=$1 B=$2 M=$3 S=$4 T=$5 strict=0
  [ "$M" = llm ] && strict=1
  BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable \
  BRIDGESENTRY_OFFICIAL_SEEDS=$M BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=$strict \
  "$BIN" --atg $ROOT/$B/llm_outputs/atg.json --scenarios $ROOT/$B/llm_outputs/hypotheses.json \
    --metadata $ROOT/$B/metadata.json --output "$E/runs/${T}_${M}_s$S.json" --budget 300 --runs 1 --seed $S \
    --source-rpc $RPC --dest-rpc $RPC --source-block 21500000 --dest-block 21500000 \
    > "$E/runs/${T}_${M}_s$S.log" 2>&1
  echo $? > "$E/runs/${T}_${M}_s$S.rc"
}
export -f one
J="$E/jobs.txt"; : > "$J"
for s in $(seq 1042 1000 20042); do
  echo "$REPO/benchmarks benign_bridge random $s paired" >> "$J"
  echo "$REPO/benchmarks benign_bridge llm $s paired" >> "$J"
done
for s in 1042 2042; do echo "$STAGE benign_bridge_unpaired llm $s unpaired" >> "$J"; done
xargs -P 7 -L1 bash -c 'one "$0" "$1" "$2" "$3" "$4"' < "$J"
date -u +"finished %Y-%m-%dT%H:%M:%SZ" >> "$E/run_info.txt"
cp "$0" "$E/campaign.sh" 2>/dev/null || true
python3 - "$E" <<'PY'
import json,glob,os,sys,csv
E=sys.argv[1]; rows=[]
for f in sorted(glob.glob(E+'/runs/*.json')):
    b=os.path.basename(f)[:-5]; cond,mode,seed=b.split('_')[0],b.split('_')[1],int(b.split('_s')[-1])
    d=json.load(open(f)); c=d.get('candidates') or []
    rc=open(f[:-5]+'.rc').read().strip()
    rows.append([cond,mode,seed,rc,d.get('candidates_total'),d.get('valid_exploits'),d.get('iterations'),
                 (d.get('coverage') or {}).get('fixture_unique_pcs'),json.dumps(c[0].get('gain')) if c else ''])
rows.sort(key=lambda r:(r[0],r[1],r[2]))
with open(E+'/summary.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['condition','seed_mode','seed','rc','candidates_total','valid_exploits','iterations','fixture_unique_pcs','gain']); w.writerows(rows)
p=[r for r in rows if r[0]=='paired']; u=[r for r in rows if r[0]=='unpaired']
it=[r[6] for r in p]
n=len(p); up=1-0.025**(1/n) if n else float('nan')
print('paired n=%d alerts=%d rc!=0:%d  CI95 upper=%.4f  iters min/med/max/total=%s/%s/%s/%s' % (
  n, sum(1 for r in p if (r[4] or 0)>0), sum(1 for r in rows if r[3]!='0'), up,
  min(it), sorted(it)[n//2], max(it), sum(it)))
for r in u: print('unpaired seed',r[2],'candidates',r[4],'gain',r[8])
PY
echo CAMPAIGN_DONE
