#!/usr/bin/env python3
"""Pre-register the Phase C production campaign on the campaign ledger:
one `preregistration` entry with the design SHA-256, a Merkle root per
submission batch PB1..PB5 (so a dropped or swapped run is detectable
per batch), and a separate commitment to the probe ground truth. The
design, this entry, and the push to git precede the CHPC submission.
Idempotent. Usage: python3 preregister_production.py
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
DESIGN = os.path.join(HERE, "production_design.json")

blob = open(DESIGN, "rb").read()
sha = hashlib.sha256(blob).hexdigest()
design = json.loads(blob)
led = Ledger(LEDGER)
if any(e["payload"].get("design_sha256") == sha for e in led.entries):
    sys.exit("already pre-registered")
roots = {}
for b in sorted({r["batch_id"] for r in design["runs"]}):
    rows = [r for r in design["runs"] if r["batch_id"] == b]
    roots[b] = merkle_root([leaf_hash(r) for r in rows])
e = led.append("preregistration", {
    "op_id": "prereg-" + design["campaign"],
    "campaign": design["campaign"], "paper": design["paper"],
    "design_file": "phase_c/production/production_design.json",
    "design_sha256": sha, "n_runs": design["n_runs"],
    "batch_merkle_roots": roots,
    "probe_truth_sha256": hashlib.sha256(json.dumps(
        design["probe_truth"], sort_keys=True).encode()).hexdigest(),
    "statement": "coverage seed batch (sha " + design["seed_design_sha256"][:12]
                 + ") pinned with ncxy=4, swapn=50, plus 4 physics probes "
                   "with ground truth fixed before any outcome",
})
assert led.verify_chain()
print("seq", e["seq"], "design", sha)
