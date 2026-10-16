#!/usr/bin/env python3
"""Hash the raw SRIM and RustBCA outputs of the implant-route study onto the ledger
before any analysis (implant_design.json, ledger seq 151). Run once."""
import glob, hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402
D = json.load(open(os.path.join(HERE, "implant_design.json")))
files = sorted(glob.glob(os.path.join(HERE, "srim_raw", "*")) + glob.glob(os.path.join(HERE, "srim_inputs", "*"))
               + [os.path.join(HERE, "rustbca_ranges.json")] + glob.glob(os.path.join(HERE, "rustbca_run", "*.toml")))
rel = lambda f: os.path.relpath(f, MT)
ign = subprocess.run(["git", "check-ignore"] + files, cwd=HERE, capture_output=True, text=True).stdout.split()
if ign:
    sys.exit(f"git would drop {ign}")
fs = {rel(f): hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
if any(e["payload"].get("op_id") == "raw-" + D["campaign"] for e in led.entries):
    sys.exit("already committed")
e = led.append("batch_result", {
    "op_id": "raw-" + D["campaign"], "campaign": D["campaign"], "prereg_seq": 151, "files_sha256": fs,
    "merkle_root": merkle_root([leaf_hash({"file": k, "sha256": v}) for k, v in sorted(fs.items())]),
    "statement": "raw SRIM-2013 (sparksone) and RustBCA (DGX) outputs, hashed before analyze_implant.py ran"})
assert led.verify_chain()
print("seq", e["seq"], len(fs), "files")
