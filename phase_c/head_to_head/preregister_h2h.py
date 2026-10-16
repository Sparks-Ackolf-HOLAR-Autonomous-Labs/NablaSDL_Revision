#!/usr/bin/env python3
"""Register the P1 head-to-head protocol on the campaign ledger before any
baseline is fitted and before the BTE oracle nodes return. Idempotent."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402
sha = hashlib.sha256(open(os.path.join(HERE, "h2h_design.json"), "rb").read()).hexdigest()
d = json.load(open(os.path.join(HERE, "h2h_design.json")))
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
if any(e["payload"].get("design_sha256") == sha for e in led.entries):
    sys.exit("already registered")
e = led.append("preregistration", {
    "op_id": "prereg-" + d["campaign"], "campaign": d["campaign"], "paper": d["paper"],
    "design_file": "phase_c/head_to_head/h2h_design.json", "design_sha256": sha,
    "predictions": sorted(d["predictions"]), "oracle_job": "CHPC 15922753 (not returned)",
    "statement": "evidence states, methods, metrics, replay rules and predictions fixed before any baseline fit and before the BTE oracle nodes exist"})
assert led.verify_chain()
open(os.path.join(HERE, "PREREGISTERED_SHA256"), "w").write(f"{sha}  h2h_design.json  ledger_seq={e['seq']}  entry_hash={e['entry_hash']}\n")
print("seq", e["seq"], sha)
