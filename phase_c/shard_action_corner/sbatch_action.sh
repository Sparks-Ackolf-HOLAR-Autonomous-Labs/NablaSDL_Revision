#!/bin/bash
# Ge-corner shard action (P1 active loop on real physics, 2026-09-29), one array task
# per run in points.txt:
#   run_id x T ncz seed ncxy swapn deck     (deck: std | amorph)
# Guest partition per the standing CHPC policy:
# guest/free first, grn061 off-limits.
# Submit: sbatch --array=0-$(($(wc -l < points.txt)-1)) sbatch_production.sh
#SBATCH --job-name=mt_shardA
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
read -r RID X T NCZ SEED NCXY SWAPN <<< "$LINE"

# Restartable by construction: a preempted-and-requeued task reruns its
# run from scratch. Every requeue is visible in sacct and is reported
# as an erasure event (P3's channel), never hidden.
mpirun -np "$SLURM_NTASKS" lmp -in in.mp_kappa3 \
  -log "results/${RID}.log" -screen none \
  -var x "$X" -var T "$T" -var ncz "$NCZ" -var seed "$SEED" \
  -var ncxy "$NCXY" -var swapn "$SWAPN" \
  -var pot "$POT" -var out "results/${RID}"

python3 analyze_mp.py "results/${RID}.log" "results/${RID}.profile" \
  "results/${RID}.json"
