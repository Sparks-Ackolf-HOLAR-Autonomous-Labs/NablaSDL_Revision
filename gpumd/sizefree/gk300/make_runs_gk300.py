#!/usr/bin/env python3
"""Build run directories + a SLURM array for one stage of the 300 K
Green-Kubo campaign. Refuses unless gk300_design.json matches
PREREGISTERED_SHA256; for a K2 stage, also refuses unless
analysis_gk300.json (from the committed K1 data) selected that box.
Usage: python3 make_runs_gk300.py K1|K2-box8|K2-box12 --out DIR [--placement grn|guest]
       python3 make_runs_gk300.py K1 --out DIR --smoke   (short syntax test, not a design run)"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "production"))
import make_runs  # noqa: E402

DESIGN = os.path.join(HERE, "gk300_design.json")
PREREG = os.path.join(HERE, "PREREGISTERED_SHA256")
ROOT = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_gk300"
GPUMD = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_v2/GPUMD/src/gpumd"
PLACEMENT = {
    "grn": ["-M granite", "-p sparks-gpu-grn", "-A sparks", "--qos=sparks-gpu-grn",
            "-w grn061", "--gres=gpu:h100nvl:1", "-t 08:00:00"],
    "guest": ["-M notchpeak", "-p notchpeak-gpu-guest", "-A owner-gpu-guest",
              "--gres=gpu:a40:1", "-t 08:00:00"],
}
ARRAY = """#!/bin/bash
#SBATCH -J gk300_{stage}
{hdr}
#SBATCH -N 1 -n 1 -c 2
#SBATCH --requeue
#SBATCH --array=0-{last}%{conc}
#SBATCH -o {root}/logs/{stage}_%A_%a.txt
# Pre-registered 300 K Green-Kubo campaign (gk300_design.json), stage {stage}; one run per task.
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
rm -f hac.out thermo.out exit_status
date -u +%FT%TZ > started
{gpumd} > run.log 2>&1
ex=$?
if [ $ex -ne 0 ] && [ ! -s hac.out ] && grep -q "CUDA Error" run.log; then
  echo "  cuda_init_fail (gpumd, exit $ex) host=$(hostname)" >> attempts; exit 3
fi
echo $ex > exit_status
date -u +%FT%TZ > finished
sha256sum hac.out thermo.out run.log run.in model.xyz gpu_model > sha256sums 2>/dev/null
"""


def run_in(r, scale=1):
    T, h = r["T_K"], r["hac"]
    nc = max(h["Nc"] // scale, 100)
    return (f"potential   {r['potential']}\n"
            f"velocity    {T} seed {r['seed']}\n"
            f"time_step   1\n"
            f"ensemble    npt_ber {T} {T} 100 0 100 1000\n"
            f"run         {max(100000 // scale, 1000)}\n"
            f"ensemble    nvt_nhc {T} {T} 100\n"
            f"run         {max(50000 // scale, 1000)}\n"
            f"ensemble    nve\n"
            f"compute_hac {h['sample_interval_steps']} {nc} {h['output_interval']}\n"
            f"dump_thermo 10000\n"
            f"run         {max(int(r['production_ns'] * 1e6) // scale, 20000)}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--out", required=True)
    ap.add_argument("--placement", choices=list(PLACEMENT), default="guest")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--potential", help="local potential path (smoke only)")
    a = ap.parse_args()
    blob = open(DESIGN, "rb").read()
    if not a.smoke:
        want = open(PREREG).read().split()[0]
        if hashlib.sha256(blob).hexdigest() != want:
            sys.exit("REFUSING: design hash differs from the pre-registered one")
    if a.stage.startswith("K2"):
        an = json.load(open(os.path.join(HERE, "analysis_gk300.json")))
        if an.get("box_star") is None or a.stage != f"K2-box{an['box_star']}":
            sys.exit(f"REFUSING: K1 analysis selected box*={an.get('box_star')}")
    runs = [r for r in json.loads(blob)["runs"] if r["stage"] == a.stage]
    assert runs, a.stage
    if a.smoke:
        runs = [dict(runs[0], potential=a.potential or runs[0]["potential"])]
    runs.sort(key=lambda r: -r["n_atoms"])  # long runs start first
    make_runs.run_in = run_in  # build() writes run.in through this hook: GK input, not HNEMD
    make_runs.build(os.path.join(a.out, "runs"), runs, 500 if a.smoke else 1)
    names = [r["run_id"] for r in runs]
    s = ARRAY.format(stage=a.stage, hdr="\n".join("#SBATCH " + h for h in PLACEMENT[a.placement]),
                     last=len(names) - 1, conc=len(names), root=ROOT,
                     names=" ".join(names), gpumd=GPUMD)
    open(os.path.join(a.out, f"array_{a.stage}_{a.placement}.sbatch"), "w").write(s)
    print(len(runs), "runs built in", a.out)


if __name__ == "__main__":
    main()
