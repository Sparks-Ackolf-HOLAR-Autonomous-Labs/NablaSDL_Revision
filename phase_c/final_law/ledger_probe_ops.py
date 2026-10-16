#!/usr/bin/env python3
"""Ledger the two operations on the production physics probes that the
final law relies on (the frozen detector emitted the first and missed
the second; FAULT_STUDY.md Result 1):
  scope-limit  N0, N1 (x 0.5 / 1500 K, x 0.7 / 1450 K): above the real
               solidus, where Tersoff keeps an intact crystal (method
               off-data); cause = physics guard, detector output
  split        N2, N3 (melt-quenched a-SiGe at 300 / 700 K): another
               phase; cause = structural metadata, post-quench PE about
               -3.85 to -3.89 eV/atom against about -4.20 for the crystal
               (production/results/structure_check.json)
Idempotent. Usage: python3 ledger_probe_ops.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
pe = json.load(open(os.path.join(MT, "phase_c", "production", "results", "structure_check.json")))
ops = [
    {"op": "scope-limit", "op_id": "scope-limit-production-near-melting-2026-09-29",
     "runs": [f"{p}_z{n}" for p in ("N0", "N1") for n in (24, 48, 96)],
     "scope_after": "outside the alloy law (T above the real solidus)",
     "cause": "physics guard (frozen detector, ledger seq 5): T >= T_solidus(x); Tersoff keeps an intact crystal there"},
    {"op": "split", "op_id": "split-production-amorphous-2026-09-29",
     "runs": sorted(pe), "scope_after": "a-SiGe (separate phase, no law claimed: 2 points)",
     "cause": "structural metadata: post-quench PE/atom " + ", ".join(f"{k} {v}" for k, v in sorted(pe.items()))
              + " eV against about -4.20 for the crystal; the kappa-only detector missed it (FAULT_STUDY.md)"},
]
for op in ops:
    if any(e["payload"].get("op_id") == op["op_id"] for e in led.entries):
        continue
    e = led.append("shard_operation", op)
    print(op["op"], "-> seq", e["seq"])
assert led.verify_chain()
