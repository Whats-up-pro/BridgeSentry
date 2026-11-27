#!/usr/bin/env bash
# A6 source-reorg demonstration on the benign_bridge fixture (empty-RPC, local).
# synchronized execution of a legitimate transfer -> no gain;
# a modeled source reorg (drop source-committed transfers) -> unbacked destination gain.
set -u
export PATH="$HOME/.foundry/bin:$HOME/.cargo/bin:$PATH"
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
cd "$REPO" || exit 2
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
OUT=/mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad/a6_reorg
mkdir -p "$OUT"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
python3 scripts/official/empty_rpc.py "$PORT" >/dev/null 2>&1 & RP=$!
trap 'kill $RP 2>/dev/null' EXIT
sleep 1
echo "empty_rpc on 127.0.0.1:$PORT"

RPC_URL="http://127.0.0.1:$PORT" \
BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable \
BRIDGESENTRY_OFFICIAL_SEEDS=llm BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1 \
BRIDGESENTRY_OFFICIAL_REORG=source \
"$BIN" --atg benchmarks/benign_bridge/llm_outputs/atg.json \
       --scenarios benchmarks/benign_bridge/llm_outputs/hypotheses.json \
       --metadata benchmarks/benign_bridge/metadata.json \
       --output "$OUT/reorg_benign_bridge.json" --budget 30 --runs 1 --seed 1042 \
       --source-rpc "http://127.0.0.1:$PORT" --dest-rpc "http://127.0.0.1:$PORT" \
       --source-block 21500000 --dest-block 21500000 > "$OUT/reorg_benign_bridge.log" 2>&1
echo "rc=$?"
echo "=== reorg result ==="
cat "$OUT/reorg_benign_bridge.json" 2>/dev/null | python3 -m json.tool 2>/dev/null || { echo "NO JSON; log tail:"; tail -15 "$OUT/reorg_benign_bridge.log"; }
echo A6_DONE
