#!/bin/bash
# mat_theory Phase B follow-up item 4: Green-Kubo feasibility for the
# pure-Si endpoint with Stillinger-Weber (pair sw supports centroid
# heat flux; Tersoff does not). One array task per seed.
# Submit:  sbatch --array=0-1 sbatch_gk.sh
#SBATCH --job-name=mt_gksw
#SBATCH --partition=notchpeak-guest
#SBATCH --account=owner-guest
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --mem=16G
#SBATCH --time=4:00:00
#SBATCH --requeue
#SBATCH --output=logs/%x_%A_%a.out
set -euo pipefail
module load openmpi/4.1.6 lammps

POT=/uufs/chpc.utah.edu/sys/installdir/r8/lammps/08022023.3/share/lammps/potentials/Si.sw
cd "$SLURM_SUBMIT_DIR"
mkdir -p results logs

SEEDS=(101 202)
SEED=${SEEDS[$SLURM_ARRAY_TASK_ID]}
TAG="gk_si_sw_T300_c6_s${SEED}"

mpirun -np "$SLURM_NTASKS" lmp -in in.gk_si_sw \
  -log "results/${TAG}.log" -screen none \
  -var T 300 -var ncell 6 -var seed "$SEED" \
  -var pot "$POT" -var out "results/${TAG}"

python3 analyze_gk_sw.py "results/${TAG}.log" "results/${TAG}.hcacf" \
  "results/${TAG}.json"
