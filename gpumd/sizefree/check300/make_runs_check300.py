#!/usr/bin/env python3
"""Build run directories + one SLURM array per stage for the size-free
check. Refuses unless check300_design.json matches PREREGISTERED_SHA256.
Usage: python3 make_runs_check300.py --out DIR   (rsync DIR to ROOT)
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "production"))
from make_runs import build  # noqa: E402

DESIGN = os.path.join(HERE, "check300_design.json")
PREREG = os.path.join(HERE, "PREREGISTERED_SHA256")
ROOT = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_check300"
GPUMD = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_v2/GPUMD/src/gpumd"

# stage -> sbatch header lines (placement only; see design protocol.placement)
PLACEMENT = {
    "C300-grn": ["-M granite", "-p sparks-gpu-grn", "-A sparks",
                 "--qos=sparks-gpu-grn", "-w grn061", "--gres=gpu:h100nvl:1",
                 "-t 05:00:00"],
    "C300-guest": ["-M notchpeak", "-p notchpeak-gpu-guest", "-A owner-gpu-guest",
                   "--gres=gpu:1", "--exclude=notch083,notch084,notch085,notch089,notch103,notch136,notch168,notch169,notch215,notch294,notch299,notch204,notch300,notch458",
                   "-t 05:00:00"],
}

ARRAY = """#!/bin/bash
#SBATCH -J sf_{short}
{hdr}
#SBATCH -N 1 -n 1 -c 2
#SBATCH --requeue
#SBATCH --array=0-{last}%{conc}
#SBATCH -o {root}/logs/{stage}_%A_%a.txt
# Pre-registered size-free 300 K check, stage {stage}; one run per task.
module purge; module load cuda/12.8.1
NAMES=({names})
name=${{NAMES[$SLURM_ARRAY_TASK_ID]}}
cd {root}/runs/$name || exit 1
if [ -f exit_status ] && [ "$(cat exit_status)" = "0" ]; then exit 0; fi
echo "$(date -u +%FT%TZ) job=$SLURM_JOB_ID restart=${{SLURM_RESTART_COUNT:-0}} host=$(hostname)" >> attempts
if ! nvidia-smi --query-gpu=name,driver_version --format=csv,noheader > gpu_model 2>&1 \\
   || grep -q "No devices" gpu_model; then
  echo "  cuda_init_fail (nvidia-smi) host=$(hostname)" >> attempts; rm -f exit_status; exit 3
fi
rm -f kappa.out thermo.out exit_status
date -u +%FT%TZ > started
{gpumd} > run.log 2>&1
ex=$?
if [ $ex -ne 0 ] && [ ! -s kappa.out ] && grep -q "CUDA Error" run.log; then
  echo "  cuda_init_fail (gpumd, exit $ex) host=$(hostname)" >> attempts; exit 3
fi
echo $ex > exit_status
date -u +%FT%TZ > finished
sha256sum kappa.out thermo.out run.log run.in model.xyz gpu_model > sha256sums 2>/dev/null
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    blob = open(DESIGN, "rb").read()
    want = open(PREREG).read().split()[0]
    got = hashlib.sha256(blob).hexdigest()
    if got != want:
        sys.exit(f"REFUSING: design sha256 {got} != pre-registered {want}")
    runs = json.loads(blob)["runs"]
    build(os.path.join(a.out, "runs"), runs)
    for stage, hdr in PLACEMENT.items():
        # placement only: seeds 57001-2 on grn061, 57003-4 on guest GPUs
        grn = stage == "C300-grn"
        names = [r["run_id"] for r in runs if (r["seed"] <= 57002) == grn]
        s = ARRAY.format(short=stage.split("-")[0],
                         hdr="\n".join("#SBATCH " + h for h in hdr),
                         last=len(names) - 1, conc=1 if stage == "C300-grn" else 8,
                         root=ROOT, stage=stage, names=" ".join(names), gpumd=GPUMD)
        open(os.path.join(a.out, f"array_{stage}.sbatch"), "w").write(s)
    print(len(runs), "runs built in", a.out)


if __name__ == "__main__":
    main()
