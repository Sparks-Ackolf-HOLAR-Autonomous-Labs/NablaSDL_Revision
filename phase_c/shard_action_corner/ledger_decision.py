#!/usr/bin/env python3
"""Append the pre-registered decision (decision.json) to the ledger as the
shard operations it prescribes. For 'scope-limit + release': release the
quarantine on the decided rows (restore, rows kept), scope-limit the
current alloy law to x <= 0.90, and open a basis-expansion candidate for
the Ge-rich dilute limit. Idempotent. Usage: python3 ledger_decision.py"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

dec = json.load(open(os.path.join(HERE, "decision.json")))
dsha = hashlib.sha256(open(os.path.join(HERE, "decision.json"), "rb").read()).hexdigest()
design = json.load(open(os.path.join(HERE, "shard_action_design.json")))
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
assert set(dec["decisions"].values()) == {"scope-limit + release"}, dec["decisions"]
common = {"action": design["action"], "decision_file": "phase_c/shard_action_corner/decision.json",
          "decision_sha256": dsha, "tests": {k: v["pass"] if "pass" in v else
                                             {b: v[b]["pass"] for b in v}
                                             for k, v in dec["tests"].items()}}
ops = [
    {"op": "restore", "op_id": "release-quarantine-ge-corner-2026-09-29",
     "runs": [f"{b}_z{n}" for b in ("C37", "C38") for n in (24, 48, 96)],
     "cause": "shard action T1 passed: two fresh seeds reproduce each quarantined point (mean |ln ratio| 0.019 to 0.035 <= 0.10); not an isolated fault"},
    {"op": "scope-limit", "op_id": "scope-limit-alloy-law-x-le-0.90-2026-09-29",
     "domain_after": {"x": [0.05, 0.90]},
     "cause": "T2 passed: kappa_inf rises steeply toward the Ge endpoint at 866 K (x 0.900: 4.46, 0.943: 6.93, 0.970: 11.46 W/mK), which the law form (x(1-x) plus x in resistivity) cannot follow; T3 passed with residual 0.086, so the 1/L extrapolation still holds there (marginally)"},
    {"op": "basis-expansion-candidate", "op_id": "candidate-dilute-ge-term-2026-09-29",
     "detail": "rows at x > 0.90 kept as valid evidence for a richer law (a dilute-limit term, e.g. resistivity rising as the mass-disorder scattering x(1-x) against a small pure-Ge resistivity); to be fitted and pre-registered as its own law, not folded silently into the current one"},
]
for op in ops:
    if any(e["payload"].get("op_id") == op["op_id"] for e in led.entries):
        continue
    e = led.append("shard_operation", dict(op, **common))
    print(op["op"], "-> seq", e["seq"])
assert led.verify_chain()
