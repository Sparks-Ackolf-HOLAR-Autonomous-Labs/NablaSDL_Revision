#!/bin/bash
# mat_theory Phase B follow-ups, one array task per point in
# points_followup.txt: `x T ncz seed ncxy swapn` per line.
# Covers RESULTS.md follow-up items 1-3: cross-section convergence
# (ncxy 6, 8), gentler swap rate (swapn 100, 200), and extra seeds at
# the larger sizes. Guest partition per the scheduling policy of
# 2026-09-25: guest/free first, grn061 not used.
# Submit:  sbatch --array=0-$(($(wc -l < points_followup.txt)-1)) sbatch_followup.sh
#SBATCH --job-name=mt_kfu
#SBATCH --partition=notchpeak-guest
#SBATCH --account=owner-guest
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --mem=24G
#SBATCH --time=4:00:00
#SBATCH --requeue
#SBATCH --output=logs/%x_%A_%a.out
set -euo pipefail
module load openmpi/4.1.6 lammps

POT=/uufs/chpc.utah.edu/sys/installdir/r8/lammps/08022023.3/share/lammps/potentials/SiCGe.tersoff
cd "$SLURM_SUBMIT_DIR"
mkdir -p results logs

LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" points_followup.txt)
read -r X T NCZ SEED NCXY SWAPN <<< "$LINE"
TAG="x${X}_T${T}_z${NCZ}_s${SEED}_a${NCXY}_w${SWAPN}"

# Restartable by construction: a preempted-and-requeued task just reruns
# its point from scratch (each point is minutes to tens of minutes).
mpirun -np "$SLURM_NTASKS" lmp -in in.mp_kappa2 \
  -log "results/${TAG}.log" -screen none \
  -var x "$X" -var T "$T" -var ncz "$NCZ" -var seed "$SEED" \
  -var ncxy "$NCXY" -var swapn "$SWAPN" \
  -var pot "$POT" -var out "results/${TAG}"

python3 analyze_mp.py "results/${TAG}.log" "results/${TAG}.profile" \
  "results/${TAG}.json"
