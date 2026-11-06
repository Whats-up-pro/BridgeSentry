#!/bin/bash
#SBATCH --account=uit
#SBATCH --partition=normal
#SBATCH --qos=mig2-35
#SBATCH --job-name=bs_reg
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:40:00
#SBATCH --output=/datastore/dungtrt/bridgesentry/logs/reg_%j.out
#SBATCH --error=/datastore/dungtrt/bridgesentry/logs/reg_%j.err
set -e
base=/datastore/$USER/bridgesentry
export PATH="$base/bin:/cm/local/apps/python3/bin:$PATH"
export REPO="$base/repo"
export BIN="$base/bin/bridgesentry-fuzzer"
echo "node=$(hostname) nproc=$(nproc)"; solc --version | tail -1; python3 --version
OUT="$base/runs/hpc_reg_${SLURM_JOB_ID}"
SEEDS="1042 2042 3042 4042 5042" bash "$REPO/scripts/official/run_matrix.sh" "$OUT" 20 4 nomad qubit
echo "=== SUMMARY ==="; cat "$OUT/summary_official.csv"
echo "JOB_DONE"
