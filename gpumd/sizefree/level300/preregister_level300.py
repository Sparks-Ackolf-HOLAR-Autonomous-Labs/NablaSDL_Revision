#!/usr/bin/env python3
"""Append the 300 K level campaign design to the campaign ledger (same
pattern as gpumd/production_v2/preregister_v2.py). Idempotent."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
DESIGN = os.path.join(HERE, "level300_design.json")


def main():
    blob = open(DESIGN, "rb").read()
    sha = hashlib.sha256(blob).hexdigest()
    d = json.loads(blob)
    led = Ledger(LEDGER)
    for e in led.entries:
        if e["payload"].get("design_sha256") == sha:
            print("already pre-registered at seq", e["seq"])
            return
    e = led.append("preregistration", {
        "op_id": "prereg-" + d["campaign"], "campaign": d["campaign"],
        "paper": d["paper"], "design_file": "gpumd/sizefree/level300/level300_design.json",
        "design_sha256": sha,
        "runs_merkle_root": merkle_root([leaf_hash(r) for r in d["runs"]]),
        "n_runs": d["n_runs"], "decision_rule": d["decision_rule"],
        "predictions": d["predictions"],
        "statement": "grid, gates, checks, decision rule and predictions fixed "
                     "before any run directory exists"})
    assert led.verify_chain()
    with open(os.path.join(HERE, "PREREGISTERED_SHA256"), "w") as f:
        f.write(f"{sha}  level300_design.json  ledger_seq={e['seq']}  "
                f"entry_hash={e['entry_hash']}\n")
    print("pre-registered seq", e["seq"], sha)


if __name__ == "__main__":
    main()
