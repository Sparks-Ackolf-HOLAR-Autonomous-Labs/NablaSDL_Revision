#!/usr/bin/env python3
"""Ledger the M1 MACE outputs BEFORE summarize_m1.py / analyze_sigec.py run:
one batch_result entry with the Merkle root over every m1/out file.
Refuses if any of the 10 tasks is missing or exited non-zero."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402
D = json.load(open(os.path.join(HERE, "sigec_design.json")))
OUT = os.path.join(HERE, "m1", "out")
tasks = ["bulk"] + [f"{x}_{s}" for x in ("0", "0.2", "0.5") for s in (1, 2, 3)]
files = {}
for t in tasks:
    for ext in (".json", ".exit_status"):
        p = os.path.join(OUT, t + ext)
        if not os.path.exists(p):
            sys.exit(f"missing {t}{ext}")
        files[t + ext] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if open(os.path.join(OUT, t + ".exit_status")).read().strip() != "0":
        sys.exit(f"task {t} did not exit 0")
leaves = [leaf_hash({"file": k, "sha256": v}) for k, v in sorted(files.items())]
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
op = "batch-" + D["campaign"] + "-M1"
if any(e["payload"].get("op_id") == op for e in led.entries):
    sys.exit("already committed")
e = led.append("batch_result", {
    "op_id": op, "campaign": D["campaign"], "stage": "M1-mace-gate", "raw_merkle_root": merkle_root(leaves),
    "n_files": len(files), "files_sha256": files, "chpc_job": "15892527 (notchpeak-guest)",
    "statement": "committed before summarize_m1.py or analyze_sigec.py was run on these files"})
assert led.verify_chain()
print("seq", e["seq"])
