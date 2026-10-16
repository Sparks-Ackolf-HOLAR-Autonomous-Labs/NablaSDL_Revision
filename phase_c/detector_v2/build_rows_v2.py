#!/usr/bin/env python3
"""Measure the two structure descriptors on every rebuilt production point
(md/*.dump.gz, md/*.log), attach them to the committed production rows
(production/results/production_rows.json, ledger 9-13), and commit the
descriptor table to the ledger (Merkle root) BEFORE detector v2 reads it.
angle_sd: s.d. of all first-shell bond angles (cutoff 2.95 A), pooled over
the 6 frames; vol_atom: NPT-averaged volume per atom.
Usage: ~/venvs/mace/bin/python build_rows_v2.py"""
import glob, gzip, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "bond_angles"))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from analyze_bad import angles, read_dump  # noqa: E402
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

desc = {}
for log in sorted(glob.glob(os.path.join(HERE, "md", "*.log"))):
    pid = os.path.basename(log)[:-4]
    vol = None
    for l in open(log):
        if l.startswith("MPT_VOL_ATOM"):
            vol = float(l.split()[1])
    dump = os.path.join(HERE, "md", pid + ".dump.gz")
    if vol is None or not os.path.exists(dump):
        sys.exit(f"incomplete rebuild {pid}")
    th = np.concatenate([angles(f, 2.95)[1] for f in read_dump(dump)])
    desc[pid] = {"point_id": pid, "vol_atom": round(vol, 6),
                 "angle_sd": round(float(th.std()), 4), "n_angles": int(len(th))}
json.dump(desc, open(os.path.join(HERE, "descriptors.json"), "w"), indent=1)
rows = json.load(open(os.path.join(MT, "phase_c", "production", "results", "production_rows.json")))
out = []
for r in rows:
    d = desc[r["run_id"].split("_")[0]]
    out.append(dict(r, vol_atom=d["vol_atom"], angle_sd=d["angle_sd"]))
json.dump(out, open(os.path.join(HERE, "rows_v2.json"), "w"), indent=1)
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
op = "commit-detector-v2-descriptors"
if not any(e["payload"].get("op_id") == op for e in led.entries):
    leaves = [leaf_hash(desc[k]) for k in sorted(desc)]
    e = led.append("batch_result", {
        "op_id": op, "campaign": "phase-c-detector-v2-2026-10-01",
        "n_points": len(desc), "merkle_root": merkle_root(leaves),
        "statement": "structure descriptors of the 44 rebuilt production points, "
                     "committed before detector v2 or any analysis read them"})
    print("committed at seq", e["seq"])
assert led.verify_chain()
print(len(desc), "points;", len(out), "rows")
