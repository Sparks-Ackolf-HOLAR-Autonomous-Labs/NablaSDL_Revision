#!/usr/bin/env python3
"""Record the addition of Yang et al. 2016 (J. Inorg. Mater. 31, 997) to P1.

Seen in the 14 Oct 2026 reference audit (no DOI in Asta), identified in
session 127 as DOI 10.15541/jim20160060 (Crossref), and added to P1 in
session 128 at the operator's discretion. The article is open access; its
PDF was read. It is the only measured SiGe-SiC pair found that differs only
by the SiC addition (same milling and sintering): 0.5 vol% SiC of about
100 nm mean diameter lowers kappa_L by 10% at 1000 K. yang2016_check.py
evaluates P1's model for the same ratio: at most 3.4% over radii 25-100 nm,
effective grains 0.1-0.5 um and both contrast limits. The coarse-SiC claim
(C3) holds: the particles cannot account for the drop, as for Zhao 2025.
"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
assert not any(e["payload"].get("op_id") == "add-source-yang2016" for e in led.entries)
sha = lambda p: hashlib.sha256(open(os.path.join(MT, p), "rb").read()).hexdigest()
fs = ["nano_sigec/yang2016/yang2016_check.py", "nano_sigec/yang2016/yang2016_check.json",
      "nano_sigec/yang2016/add_yang2016.py"]
chk = json.load(open(os.path.join(HERE, "yang2016_check.json")))["summary_0p5vol"]
e = led.append("shard_operation", {"op": "strengthen", "op_id": "add-source-yang2016",
    "files_sha256": {f: sha(f) for f in fs},
    "source": {"doi": "10.15541/jim20160060", "access": "open (publisher PDF read)"},
    "claim": "C3: SiC of about 50 nm radius and above lowers kappa_L by a few percent at most",
    "measured": "0.5 vol% SiC (mean diameter about 100 nm) vs same-milling SiGe: kappa_L -10% at 1000 K",
    "model_range_pct": [chk["largest_model_reduction_pct"], chk["smallest_model_reduction_pct"]],
    "trigger": "reference audit 2026-10-14 (seen, not verified); operator left the P1 decision to the agent, issue 55, 2026-10-14",
    "consequence": "second measured SiGe-SiC study whose kappa drop exceeds what its SiC particles can scatter; "
                   "C3 gains an independent witness, no number in P1 changes",
    "statement": "Yang 2016 p-type Si80Ge20B0.6-SiC nanocomposite added to P1 as a second test of the coarse-SiC claim"})
assert led.verify_chain(); print(e["seq"])
