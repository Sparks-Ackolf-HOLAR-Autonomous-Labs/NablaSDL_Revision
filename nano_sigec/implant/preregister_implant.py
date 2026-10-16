#!/usr/bin/env python3
"""Append the implant-route (SRIM) pre-registration to the campaign ledger.
Idempotent on the design hash. Commit and push before any production run."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
blob = open(os.path.join(HERE, "implant_design.json"), "rb").read()
sha = hashlib.sha256(blob).hexdigest()
d = json.loads(blob)
led = Ledger(LEDGER)
if any(e["payload"].get("design_sha256") == sha for e in led.entries):
    sys.exit("already registered")
e = led.append("preregistration", {
    "op_id": "prereg-" + d["campaign"], "campaign": d["campaign"], "paper": d["paper"],
    "design_file": "nano_sigec/implant/implant_design.json", "design_sha256": sha,
    "gates": sorted(d["decision_rule"]), "predictions": sorted(d["predictions"]),
    "statement": ("design, grid, constants, gates and predictions fixed before any dopant channel was "
                  "made for these recipes; "
                  "the only earlier SRIM runs are the three 30 keV install cross-checks"),
})
assert led.verify_chain()
open(os.path.join(HERE, "PREREGISTERED_SHA256"), "w").write(
    f"{sha}  implant_design.json  ledger_seq={e['seq']}  entry_hash={e['entry_hash']}\n")
print("seq", e["seq"], sha)
