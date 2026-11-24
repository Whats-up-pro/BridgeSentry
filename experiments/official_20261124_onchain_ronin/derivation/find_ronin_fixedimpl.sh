#!/usr/bin/env bash
set -u
export PATH="$HOME/.foundry/bin:$PATH"
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
PROXY=0x64192819ac13ef72bf6b5ae239ac672b43a9af08
IMPL=0xfc274ec92bbb1a1472884558d1b5caac6f8220ee
CD=$(cat /mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad/ronin_seed_calldata.txt)
L=http://127.0.0.1:8553
FROM=0x000000000000000000000000000000000000dEaD
IMPLSLOT=0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc  # EIP-1967 implementation slot

echo "buggy impl @fork  : $(cast storage $PROXY $IMPLSLOT --rpc-url $ETH --block 20468678)"
FIXEDRAW=$(cast storage $PROXY $IMPLSLOT --rpc-url $ETH --block latest)
echo "impl @latest      : $FIXEDRAW"
FIXEDADDR=0x${FIXEDRAW: -40}
echo "fixed impl addr   : $FIXEDADDR"

anvil --fork-url "$ETH" --fork-block-number 20468678 --port 8553 --silent >/tmp/anvil_ronin3.log 2>&1 &
APID=$!
trap 'kill $APID 2>/dev/null' EXIT
for i in $(seq 1 40); do cast block-number --rpc-url $L >/dev/null 2>&1 && break; sleep 1; done
echo "anvil up @ $(cast block-number --rpc-url $L)"

echo "=== baseline (buggy impl) exploit call ==="
cast call $PROXY $CD --rpc-url $L --from $FROM 2>&1 | head -1

# fetch fixed impl runtime code from the real node (latest) and overlay it at the buggy impl address
CODE=$(cast code $FIXEDADDR --rpc-url "$ETH")
echo "fixed impl code len chars: ${#CODE}"
cast rpc anvil_setCode $IMPL "$CODE" --rpc-url $L >/dev/null 2>&1
echo "=== after code-overlay with REAL fixed impl: exploit call (should revert if fix is code-level) ==="
cast call $PROXY $CD --rpc-url $L --from $FROM 2>&1 | head -3
