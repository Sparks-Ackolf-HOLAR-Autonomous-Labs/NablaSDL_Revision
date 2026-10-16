#!/bin/bash
# Guest partition only (standing directive: guest/free first, grn061 off-limits; DGX reserved).
#SBATCH --job-name=mt_sigec_m1
#SBATCH --partition=notchpeak-guest
#SBATCH --account=owner-guest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --requeue
#SBATCH --array=0-9
#SBATCH --output=logs/%x_%A_%a.out
TASKS=(bulk 0_1 0_2 0_3 0.2_1 0.2_2 0.2_3 0.5_1 0.5_2 0.5_3)
cd "$SLURM_SUBMIT_DIR"; mkdir -p logs out
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
P=/uufs/chpc.utah.edu/sys/installdir/r8/mace/0.3.16_cu126/.venv/bin/python
T=${TASKS[$SLURM_ARRAY_TASK_ID]}
$P mace_gate.py "$T" && echo 0 > out/$T.exit_status || echo $? > out/$T.exit_status
