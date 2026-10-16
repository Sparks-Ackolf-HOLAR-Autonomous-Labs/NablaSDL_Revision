#!/usr/bin/env python3
"""Commit one finished stage of the 300 K Green-Kubo campaign (pattern of ../level300/commit_level300.py) to the
ledger BEFORE it is analysed: copy each run's raw outputs into the repo
(`raw/<run_id>/`), hash them, and append a `batch_result` entry with the
Merkle root over the per-run leaves (run_id + file hashes). Refuses to
commit a stage with unfinished runs, and is idempotent per stage.

Usage: python3 commit_gk300.py K1 [--root DIR]   (DIR = local copy of the run directories)
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
FILES = ("hac.out", "thermo.out", "run.log", "run.in", "exit_status",
         "started", "finished", "gpu_model", "attempts")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--root", default=os.path.expanduser(
        "~/mat_theory_gk300_stage/runs"))
    a = ap.parse_args()
    design = json.load(open(os.path.join(HERE,
                                         "gk300_design.json")))
    runs = [r for r in design["runs"] if r["stage"] == a.stage]
    assert runs, f"unknown stage {a.stage}"
    led = Ledger(LEDGER)
    op_id = f"commit-{design['campaign']}-{a.stage}"
    if any(e["payload"].get("op_id") == op_id for e in led.entries):
        sys.exit(f"{a.stage} already committed")
    leaves, manifest = [], {}
    for r in runs:
        src = os.path.join(a.root, r["run_id"])
        if not os.path.exists(os.path.join(src, "exit_status")):
            sys.exit(f"REFUSING: {r['run_id']} not finished")
        dst = os.path.join(HERE, "raw", r["run_id"])
        os.makedirs(dst, exist_ok=True)
        hashes = {}
        for f in FILES:
            if os.path.exists(os.path.join(src, f)):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
                hashes[f] = sha(os.path.join(dst, f))
        for f in hashes:
            # refuse evidence git would silently drop (an earlier commit lost files this way:
            # the repo-wide *.out / *.log ignore kept raw files out of git)
            if subprocess.run(["git", "check-ignore", "-q", os.path.join(dst, f)],
                              cwd=HERE).returncode == 0:
                sys.exit(f"REFUSING: {dst}/{f} is git-ignored; fix .gitignore first")
        manifest[r["run_id"]] = hashes
        leaves.append(leaf_hash({"run_id": r["run_id"], "files": hashes}))
    json.dump(manifest, open(os.path.join(HERE, "raw",
                                          f"manifest_{a.stage}.json"), "w"),
              indent=1, sort_keys=True)
    e = led.append("batch_result", {
        "op_id": op_id, "campaign": design["campaign"], "stage": a.stage,
        "n_runs": len(runs), "merkle_root": merkle_root(leaves),
        "statement": "raw outputs committed before analysis"})
    assert led.verify_chain()
    print(a.stage, "committed at seq", e["seq"])


if __name__ == "__main__":
    main()
