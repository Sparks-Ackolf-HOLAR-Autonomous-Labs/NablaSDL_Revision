#!/usr/bin/env python3
"""Commit the collected shard-action results to the ledger (Merkle root
over per-run file hashes) BEFORE decide.py reads them. Refuses if any
design run is missing. Idempotent. Usage: python3 commit_results.py"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

d = json.load(open(os.path.join(HERE, "shard_action_design.json")))
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
op_id = "commit-" + d["action"]
if any(e["payload"].get("op_id") == op_id for e in led.entries):
    sys.exit("already committed")
leaves, man = [], {}
for r in d["runs"]:
    h = {}
    for ext in ("json", "log", "profile"):
        p = os.path.join(HERE, "results", f"{r['run_id']}.{ext}")
        if not os.path.exists(p):
            sys.exit(f"REFUSING: missing {p}")
        h[ext] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    man[r["run_id"]] = h
    leaves.append(leaf_hash({"run_id": r["run_id"], "files": h}))
json.dump(man, open(os.path.join(HERE, "results", "manifest.json"), "w"), indent=1, sort_keys=True)
e = led.append("batch_result", {"op_id": op_id, "action": d["action"], "n_runs": len(leaves),
                                "merkle_root": merkle_root(leaves),
                                "statement": "raw outputs committed before the decision rule is applied",
                                "infrastructure_notes": [a[len("--note="):] for a in sys.argv[1:] if a.startswith("--note=")]})
assert led.verify_chain()
print("seq", e["seq"])
