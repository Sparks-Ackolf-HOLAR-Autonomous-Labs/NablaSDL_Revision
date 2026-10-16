#!/usr/bin/env python3
"""Hash the 14 x 3 BTE oracle outputs (copied into oracle/ from CHPC
party4_bte/results) onto the ledger before head_to_head.py reads them."""
import glob, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, merkle_root  # noqa: E402
files = sorted(glob.glob(os.path.join(HERE, "oracle", "bte_x*_T*.json")))
assert len(files) == 42, len(files)
leaves = [hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files]
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
root = merkle_root(leaves)
if any(e["payload"].get("merkle_root") == root for e in led.entries):
    sys.exit("already committed")
e = led.append("commit", {"op_id": "commit-h2h-bte-oracle-2026-09-30", "campaign": "p1-head-to-head-2026-09-30",
                          "paper": "P1", "job": "CHPC 15922753", "n_files": len(files), "merkle_root": root,
                          "files": {os.path.basename(f): h for f, h in zip(files, leaves)},
                          "statement": "oracle outputs hashed before head_to_head.py read them"})
assert led.verify_chain()
print("seq", e["seq"], root)
