#!/bin/bash
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --qos=mig2-35
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=01:30:00
#SBATCH --output=/datastore/dungtrt/bridgesentry/logs/%x_%j.out
#SBATCH --error=/datastore/dungtrt/bridgesentry/logs/%x_%j.err
set -e
base=/datastore/$USER/bridgesentry
export PATH="$base/bin:/cm/local/apps/python3/bin:$PATH"
export REPO="$base/repo" BIN="$base/bin/$BINNAME"
echo "node=$(hostname) BIN=$BIN"; sha256sum "$BIN"; solc --version|tail -1
OUT="$base/runs/${OUTTAG}_${SLURM_JOB_ID}"
SEEDS="1042 2042 3042 4042 5042" bash "$REPO/scripts/official/run_matrix.sh" "$OUT" 600 4 feg_bridge_2024 crosscurve polynetwork
echo "=== SUMMARY ($OUTTAG) ==="; cat "$OUT/summary_official.csv"; echo JOB_DONE
