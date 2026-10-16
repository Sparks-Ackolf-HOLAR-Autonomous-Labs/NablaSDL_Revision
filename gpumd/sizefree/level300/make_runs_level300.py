#!/usr/bin/env python3
"""Build run directories + SLURM arrays for one stage of the 300 K level
campaign. Refuses unless level300_design.json matches PREREGISTERED_SHA256.
For an L2 stage, also refuses unless analysis_level300.json (from the
committed L1 data) selected that box length.
Usage: python3 make_runs_level300.py L1|L2-box16|L2-box32 --out DIR
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "production"))
from make_runs import build  # noqa: E402

DESIGN = os.path.join(HERE, "level300_design.json")
PREREG = os.path.join(HERE, "PREREGISTERED_SHA256")
ROOT = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_level300"
GPUMD = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_v2/GPUMD/src/gpumd"
PLACEMENT = {
    "grn": ["-M granite", "-p sparks-gpu-grn", "-A sparks", "--qos=sparks-gpu-grn",
            "-w grn061", "--gres=gpu:h100nvl:1", "-t 06:00:00"],
    "guest": ["-M notchpeak", "-p notchpeak-gpu-guest", "-A owner-gpu-guest",
              "--gres=gpu:a40:1", "-t 06:00:00"],
}
ARRAY = open(os.path.join(HERE, "..", "check300", "make_runs_check300.py")).read()
ARRAY = ARRAY.split('ARRAY = """', 1)[1].split('"""', 1)[0]
ARRAY = ARRAY.replace("size-free 300 K check", "300 K level campaign")
# the source holds "\\\\" (escaped in its string literal); undo the escape
ARRAY = ARRAY.replace("\\\\\n", "\\\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--out", required=True)
    ap.add_argument("--placement", choices=list(PLACEMENT), default="guest")
    a = ap.parse_args()
    blob = open(DESIGN, "rb").read()
    want = open(PREREG).read().split()[0]
    if hashlib.sha256(blob).hexdigest() != want:
        sys.exit("REFUSING: design hash differs from the pre-registered one")
    if a.stage.startswith("L2"):
        an = json.load(open(os.path.join(HERE, "analysis_level300.json")))
        if an.get("Lstar") is None or a.stage != f"L2-box{an['Lstar']}":
            sys.exit(f"REFUSING: L1 analysis selected Lstar={an.get('Lstar')}")
    runs = [r for r in json.loads(blob)["runs"] if r["stage"] == a.stage]
    assert runs, a.stage
    # largest boxes first so the long runs start earliest
    runs.sort(key=lambda r: -r["n_atoms"])
    build(os.path.join(a.out, "runs"), runs)
    names = [r["run_id"] for r in runs]
    s = ARRAY.format(short="L3", hdr="\n".join("#SBATCH " + h for h in PLACEMENT[a.placement]),
                     last=len(names) - 1, conc=len(names), root=ROOT,
                     stage=a.stage, names=" ".join(names), gpumd=GPUMD)
    open(os.path.join(a.out, f"array_{a.stage}_{a.placement}.sbatch"), "w").write(s)
    print(len(runs), "runs built in", a.out)


if __name__ == "__main__":
    main()
