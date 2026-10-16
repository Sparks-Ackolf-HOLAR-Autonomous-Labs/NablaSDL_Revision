#!/usr/bin/env python3
"""Build the detector-facing production table from results/*.json and
commit it: one ledger `batch_result` entry per complete submission
batch (PB1..PB5), Merkle root over the batch's run rows, appended BEFORE
the detector or any analysis reads them. Rows carry only
{run_id, batch_id, party, x, T, ncz, seed, kappa, n_atoms}; the deck
(std/amorph) and the probe truth are not exposed.

Also writes results/structure_check.json with the post-quench
potential energy per atom of the amorphous probes (MPT_PE_ATOM), the
physical check that the melt-quench actually amorphized.
Usage: python3 build_rows.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

design = json.load(open(os.path.join(HERE, "production_design.json")))
byid = {r["run_id"]: r for r in design["runs"]}
rows, pe = [], {}
for f in sorted(glob.glob(os.path.join(HERE, "results", "*.json"))):
    rid = os.path.basename(f)[:-5]
    if rid not in byid or rid in ("production_rows", "structure_check"):
        continue
    j = json.load(open(f))
    d = byid[rid]
    rows.append({"run_id": rid, "batch_id": d["batch_id"],
                 "party": "CHPC-MD-C", "x": d["x"], "T": float(d["T"]),
                 "ncz": d["ncz"], "seed": d["seed"],
                 "kappa": j["kappa_W_mK"], "n_atoms": j["natoms"]})
    if d["deck"] == "amorph":
        for l in open(f[:-5] + ".log"):
            if l.startswith("MPT_PE_ATOM"):
                pe[rid] = float(l.split()[1])
json.dump(rows, open(os.path.join(HERE, "results", "production_rows.json"),
                     "w"), indent=1)
json.dump(pe, open(os.path.join(HERE, "results", "structure_check.json"),
                   "w"), indent=1)
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
done = {e["payload"].get("op_id") for e in led.entries}
have = {r["run_id"] for r in rows}
for b in sorted({r["batch_id"] for r in design["runs"]}):
    want = [r["run_id"] for r in design["runs"] if r["batch_id"] == b]
    op = f"commit-{design['campaign']}-{b}"
    if op in done or not set(want) <= have:
        continue
    br = sorted([r for r in rows if r["batch_id"] == b],
                key=lambda r: r["run_id"])
    e = led.append("batch_result", {
        "op_id": op, "campaign": design["campaign"], "batch_id": b,
        "n_runs": len(br), "merkle_root": merkle_root([leaf_hash(r)
                                                       for r in br]),
        "statement": "detector-facing rows committed before detection"})
    print(b, "committed at seq", e["seq"])
assert led.verify_chain()
print(len(rows), "rows;", len(pe), "amorphous PE checks")
