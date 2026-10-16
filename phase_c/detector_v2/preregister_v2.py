#!/usr/bin/env python3
"""Append the detector v2 pre-registration (design + code hashes) to the
campaign ledger. Idempotent on the design hash. Push before any rebuild."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402
blob = open(os.path.join(HERE, "design_v2.json"), "rb").read()
sha = hashlib.sha256(blob).hexdigest()
d = json.loads(blob)
files = {f: hashlib.sha256(open(os.path.join(MT, f), "rb").read()).hexdigest() for f in d["files"]}
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
if any(e["payload"].get("design_sha256") == sha for e in led.entries):
    sys.exit("already registered")
e = led.append("preregistration", {
    "op_id": "prereg-" + d["campaign"], "campaign": d["campaign"], "paper": d["paper"],
    "design_file": "phase_c/detector_v2/design_v2.json", "design_sha256": sha,
    "files_sha256": files, "predictions": sorted(d["predictions"]),
    "statement": "detector v2 code, harness, attachment rule, predictions and decision rule fixed "
                 "before any structure descriptor of the production points existed; only a "
                 "synthetic-descriptor crash test (selftest_v2.py) was run"})
assert led.verify_chain()
open(os.path.join(HERE, "PREREGISTERED_SHA256"), "w").write(
    f"{sha}  design_v2.json  ledger_seq={e['seq']}  entry_hash={e['entry_hash']}\n")
print("seq", e["seq"], sha)
