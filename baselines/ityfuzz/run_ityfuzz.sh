#!/usr/bin/env bash
# run_ityfuzz.sh <harness_dir> <variant:vuln|patched> <seed> <budget_s> <out_dir>
#
# One ItyFuzz run (single-chain baseline, RQ2/C2) on one BridgeSentry fixture
# harness. Offline: expects forge + a cached solc 0.8.20 (~/.svm/0.8.20) and the
# ItyFuzz binary at $ITYFUZZ. Fairness: attacker senders are pinned by the
# harness `targetSenders()`; --concolic-caller is NOT used.
#
# Writes <out>/seed_<seed>.log (full ItyFuzz output) and <out>/seed_<seed>.result
# (one line: "<detected 0|1> <tte_s or -1> rc=<rc>").
set -u
HARN=$1; VARIANT=$2; SEED=$3; BUDGET=$4; OUT=$5
ITYFUZZ=${ITYFUZZ:?set ITYFUZZ to the ityfuzz binary}
PROJ="$HARN/$VARIANT"
[ -d "$PROJ/src" ] || { echo "run_ityfuzz: no $PROJ/src" >&2; exit 2; }
export PATH="$HOME/.foundry/bin:$PATH"
export FOUNDRY_OFFLINE=true
mkdir -p "$OUT"
LOG="$OUT/seed_$SEED.log"
cd "$PROJ" || exit 2
# Compile once (idempotent; forge caches). Offline, uses the cached solc 0.8.20.
forge build --offline >/dev/null 2>&1
# ItyFuzz runs `forge build` itself (from_command) to load the build artifacts,
# then fuzzes from Harness.setUp(). Invariant oracle flags a revert of
# invariant_bridgeSafe (= a net adversary gain of a bridged asset).
timeout "$BUDGET" "$ITYFUZZ" evm \
  -m src/Harness.sol:Harness -f --detectors invariant --seed "$SEED" \
  forge build > "$LOG" 2>&1
rc=$?
det=0; tte=-1
if grep -q "Found vulnerabilities!" "$LOG"; then
  det=1
  # TTE ~ run time of the last stats/testcase line before the bug (ItyFuzz exits
  # on the first objective). Format: "run time: 0h-0m-5s".
  rt=$(grep -oE "run time: [0-9]+h-[0-9]+m-[0-9]+s" "$LOG" | tail -1)
  if [ -n "$rt" ]; then
    h=$(echo "$rt" | grep -oE "[0-9]+h" | tr -d h)
    m=$(echo "$rt" | grep -oE "[0-9]+m" | tr -d m)
    s=$(echo "$rt" | grep -oE "[0-9]+s" | tr -d s)
    tte=$(( ${h:-0}*3600 + ${m:-0}*60 + ${s:-0} ))
  else
    tte=0
  fi
fi
echo "$det $tte rc=$rc" > "$OUT/seed_$SEED.result"
echo "$HARN $VARIANT seed=$SEED detected=$det tte=${tte}s rc=$rc"
exit 0
