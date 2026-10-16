#!/usr/bin/env python3
"""Put the x=0.7 acquisition design on the campaign ledger (design SHA-256 +
Merkle root over the run rows) BEFORE any run is submitted. Idempotent.
Usage: python3 design_acquisition.py && python3 preregister.py
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

blob = open(os.path.join(HERE, "acquisition_design.json"), "rb").read()
sha = hashlib.sha256(blob).hexdigest()
d = json.loads(blob)
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
if any(e["payload"].get("design_sha256") == sha for e in led.entries):
    sys.exit("already pre-registered")
e = led.append("preregistration", {
    "op_id": "prereg-" + d["action"], "action": d["action"],
    "decides": d["decides"],
    "design_file": "phase_c/acquisition_x07/acquisition_design.json",
    "design_sha256": sha, "n_runs": len(d["runs"]),
    "runs_merkle_root": merkle_root([leaf_hash(r) for r in d["runs"]]),
    "statement": "first autonomous acquisition: one almaBTE point bought to decide "
                 "between two calibrations; predictions and decision rule fixed before any run"})
assert led.verify_chain()
open(os.path.join(HERE, "PREREGISTERED_SHA256"), "w").write(sha + "\n")
print("seq", e["seq"], "design", sha)
