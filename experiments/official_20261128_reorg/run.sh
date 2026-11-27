#!/usr/bin/env bash
# A6 rerun with full provenance: release build at commit 9c21535, solc 0.8.20.
set -u
export PATH=/root/.local/solc0820:$HOME/.cargo/bin:$PATH
REPO=/mnt/d/HK1_2026-2027/NT505/BridgeSentry
E=$REPO/experiments/official_20261128_reorg
mkdir -p "$E"
cd "$REPO/src/module3_fuzzing" || exit 2
cargo build --release > "$E/build.log" 2>&1 || { echo BUILD_FAIL; tail -20 "$E/build.log"; exit 3; }
cargo test --release > "$E/cargo_test.log" 2>&1; echo "cargo_test_exit=$?" > "$E/cargo_test.rc"
cd "$REPO"
BIN=src/module3_fuzzing/target/release/bridgesentry-fuzzer
{
  echo "commit $(git rev-parse HEAD)"
  echo "worktree_clean_src: $(git status --porcelain src | wc -l) modified src files"
  sha256sum "$BIN"
  echo "solc: $(readlink -f "$(command -v solc)")"; sha256sum "$(readlink -f "$(command -v solc)")"; solc --version | tail -1
  rustc --version; uname -sr; nproc
  echo "host: developer workstation (WSL2), local empty-RPC (not a mainnet fork)"
} > "$E/run_info.txt"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
python3 scripts/official/empty_rpc.py "$PORT" >/dev/null 2>&1 & RP=$!
trap 'kill $RP 2>/dev/null' EXIT
sleep 1
for S in 1042 2042 3042; do
  RPC_URL="http://127.0.0.1:$PORT" \
  BRIDGESENTRY_EVALUATION_MODE=official BRIDGESENTRY_OFFICIAL_VARIANT=vulnerable \
  BRIDGESENTRY_OFFICIAL_SEEDS=llm BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1 \
  BRIDGESENTRY_OFFICIAL_REORG=source \
  "$BIN" --atg benchmarks/benign_bridge/llm_outputs/atg.json \
         --scenarios benchmarks/benign_bridge/llm_outputs/hypotheses.json \
         --metadata benchmarks/benign_bridge/metadata.json \
         --output "$E/reorg_benign_bridge_s$S.json" --budget 30 --runs 1 --seed "$S" \
         --source-rpc "http://127.0.0.1:$PORT" --dest-rpc "http://127.0.0.1:$PORT" \
         --source-block 21500000 --dest-block 21500000 > "$E/reorg_benign_bridge_s$S.log" 2>&1
  echo "seed $S rc=$?"
done
cp "$0" "$E/run.sh" 2>/dev/null || true
cat "$E/run_info.txt"; cat "$E/cargo_test.rc"; grep -E "^test result|benign_bridge" "$E/cargo_test.log"
python3 -c "
import json,glob
for f in sorted(glob.glob('$E/reorg_benign_bridge_s*.json')):
    d=json.load(open(f)); print(f.split('/')[-1], 'sync=',d['synchronized_gains'],'reorged=',d['source_reorged_gains'],'transfers=',d['transfers_executed'])
"
