#!/usr/bin/env python3
"""Apply the registered decision rule (design_v2.json) from results_v2.json:
adopt -> ledger `commitment` (detector v2 is the E1 entry check for MD
parties); reject -> ledger `gate_failure` naming the failed predictions."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402
res = json.load(open(os.path.join(HERE, "results_v2.json")))
sha = lambda f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
camp = "phase-c-detector-v2-2026-10-01"
if any(e["payload"].get("op_id") == "decision-" + camp for e in led.entries):
    sys.exit("already applied")
P = res["predictions"]
common = {"campaign": camp, "op_id": "decision-" + camp,
          "results_sha256": {"results_v2.json": sha("results_v2.json"),
                             "fault_study_results_v2.json": sha("fault_study_results_v2.json")},
          "predictions": {k: v["pass"] for k, v in P.items()}}
if res["adopt"]:
    e = led.append("commitment", dict(common, decision="adopt",
        statement="registered rule met (Pr1-Pr5, Pr7): detector v2 becomes the E1 entry "
                  "check for MD parties; Pr6 recorded as the stated limit"))
else:
    failed = [k for k in ("Pr1", "Pr2", "Pr3", "Pr4", "Pr5", "Pr7") if not P[k]["pass"]]
    e = led.append("gate_failure", dict(common, decision="reject", failed=failed,
        statement="registered rule not met; v1 with D2 stays the entry check; "
                  "v2 thresholds not edited within this registration"))
assert led.verify_chain()
print("seq", e["seq"], e["kind"])
