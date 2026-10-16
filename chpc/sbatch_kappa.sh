#!/bin/bash
# mat_theory Phase B kappa campaign, one array task per (x, T, ncz, seed)
# point in points.txt. Guest partition per the scheduling policy of
# 2026-09-25: guest/free first, grn061 not used.
# Submit:  sbatch --array=0-$(($(wc -l < points.txt)-1)) sbatch_kappa.sh
#SBATCH --job-name=mt_kappa
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

LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" points.txt)
read -r X T NCZ SEED <<< "$LINE"
TAG="x${X}_T${T}_z${NCZ}_s${SEED}"

# Restartable by construction: a preempted-and-requeued task just reruns
# its point from scratch (each point is minutes to tens of minutes).
mpirun -np "$SLURM_NTASKS" lmp -in in.mp_kappa \
  -log "results/${TAG}.log" -screen none \
  -var x "$X" -var T "$T" -var ncz "$NCZ" -var seed "$SEED" \
  -var pot "$POT" -var out "results/${TAG}"

python3 analyze_mp.py "results/${TAG}.log" "results/${TAG}.profile" \
  "results/${TAG}.json"
