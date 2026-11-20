#!/usr/bin/env bash
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --qos=mig2-35
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=07:00:00
#SBATCH --output=logs/ityfuzz_%j.out
#SBATCH --error=logs/ityfuzz_%j.err
#
# ItyFuzz single-chain baseline (RQ2 / contribution C2) on the seven on-chain
# fixtures. CPU-only (no --gres), per Huong_dan_HPC_dungtrt.pdf. Runs one
# VARIANT (vulnerable or patched) of all seven fixtures, 20 seeds x 300 s,
# 8 runs in parallel (xargs -P). Submit twice: VARIANT=vuln and VARIANT=patched.
#
# Ship beforehand to $ROOT (via scp, "prepare files"):
#   - ityfuzz            : the ItyFuzz binary (must run on the compute node;
#                          verify glibc or ship a portable build)
#   - foundry/bin/forge  : the forge binary
#   - svm/0.8.20/solc-0.8.20 : cached solc so `forge build --offline` needs no net
#   - harness/           : baselines/ityfuzz/harness (the 7 fixtures x {vuln,patched})
#   - run_ityfuzz.sh, aggregate_ityfuzz.py
# Env (export before sbatch, or edit here):
#   ROOT   : staging dir on /datastore/dungtrt (holds the files above)
#   VARIANT: vuln | patched
set -u
ROOT=${ROOT:?set ROOT to the staging dir on /datastore/dungtrt}
VARIANT=${VARIANT:?set VARIANT=vuln or VARIANT=patched}
BUDGET=${BUDGET:-300}
SEEDS=${SEEDS:-"1042 2042 3042 4042 5042 6042 7042 8042 9042 10042 11042 12042 13042 14042 15042 16042 17042 18042 19042 20042"}
FIXTURES=${FIXTURES:-"ronin_2024 nomad crosscurve verus qubit feg_bridge_2024 polynetwork"}

export ITYFUZZ="$ROOT/ityfuzz"
export HOME_FOUNDRY="$ROOT/foundry"
export PATH="$HOME_FOUNDRY/bin:$PATH"
# Point svm/foundry at the shipped, pre-cached solc so no download is attempted.
export SVM_DATA_DIR="$ROOT/svm"          # forge/svm solc cache root (holds 0.8.20/)
export FOUNDRY_OFFLINE=true
mkdir -p "$ROOT/svm" "$HOME/.svm" 2>/dev/null
# forge looks up ~/.svm/<ver>/solc-<ver>; link the shipped cache into place.
ln -sfn "$ROOT/svm/0.8.20" "$HOME/.svm/0.8.20" 2>/dev/null || cp -rn "$ROOT/svm/0.8.20" "$HOME/.svm/" 2>/dev/null

OUTROOT="$ROOT/runs_$VARIANT"
JOBS="$ROOT/jobs_$VARIANT.txt"
: > "$JOBS"
for b in $FIXTURES; do
  for s in $SEEDS; do
    echo "$ROOT/harness/$b $VARIANT $s $BUDGET $OUTROOT/$b/$VARIANT" >> "$JOBS"
  done
done

echo "node=$(hostname) variant=$VARIANT runs=$(wc -l < "$JOBS") budget=${BUDGET}s"
echo "ityfuzz=$("$ITYFUZZ" --version 2>&1 | head -1 || echo MISSING)"
echo "forge=$(forge --version 2>&1 | head -1 || echo MISSING)"

# 8 runs in parallel; each line -> run_ityfuzz.sh <harness_dir> <variant> <seed> <budget> <out>
xargs -P 8 -L 1 bash "$ROOT/run_ityfuzz.sh" < "$JOBS"

echo "=== aggregate ($VARIANT) ==="
python3 "$ROOT/aggregate_ityfuzz.py" "$OUTROOT" "$BUDGET" | tee "$ROOT/summary_ityfuzz_$VARIANT.csv"
