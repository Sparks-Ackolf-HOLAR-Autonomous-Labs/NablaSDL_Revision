#!/usr/bin/env python3
"""Ledger the shard operations the independent second extractor's value
audit justifies (agreement.json). Each operation names its identified
cause, so the two-bar rule is met by an independent confirmation (a
second extractor from a different model family) rather than a
statistical verdict alone. Rows are addressed by stage0 row_id =
ledger.leaf_hash(raw point dict); the extracted_points.json file itself
is not edited (artifacts are retained; influence is what changes).
Operations:
  scope-limit  15 non-SiGe-family rows (GeSn, SiSn, Sn, BiSbTe) leave the
               SiGe literature party's scope (re-tag other-system)
  forget       rows 29, 30: value absent from the source snippet
  correct      row 34: x_ge 1 -> 0.2 (the quoted ~9 W/mK is the 20% Ge value)
  quarantine   row 33 (bulk-SiGe range attributed to pure Si, true x unknown),
               rows 17-20 (x is a Ni/B dopant level, Ge fraction not stated),
               7 derived values (8, 9, 40, 41, 53, 54, 55: arithmetic on
               snippet numbers, not reported measurements)
Usage: python3 ledger_value_audit.py [--dry-run]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger, leaf_hash, merkle_root  # noqa: E402

pts = json.load(open(os.path.join(MT, "pilot", "kg", "extracted_points.json")))
ag = json.load(open(os.path.join(HERE, "agreement.json")))
rid = lambda i: leaf_hash(pts[i])
non = sorted(r["row"] for r in ag["non_SiGe_family_rows"]["rows"])
absent = sorted(r["row"] for r in ag["value_not_in_snippet"]["rows"] if r["value_note"] == "absent")
derived = sorted(r["row"] for r in ag["value_not_in_snippet"]["rows"] if r["value_note"] == "derived")
assert set(absent) <= set(non)
assert pts[34]["x_ge"] == 1 and pts[33]["x_ge"] == 0
ops = [
    {"op": "scope-limit", "op_id": "scope-limit-literature-non-SiGe-2026-09-29",
     "rows": [rid(i) for i in non if i not in absent], "kg_index": [i for i in non if i not in absent],
     "scope_after": "literature-other-system (outside the SiGe law's evidence)",
     "cause": "second extractor: quoted value is for GeSn / SiSn / Sn / BiSbTe, not Si1-xGex"},
    {"op": "forget", "op_id": "forget-literature-absent-values-2026-09-29",
     "rows": [rid(i) for i in absent], "kg_index": absent,
     "cause": "value absent from the source snippet (candidate extraction hallucination), confirmed by an independent second extractor"},
    {"op": "correct", "op_id": "correct-literature-row34-x-2026-09-29",
     "rows": [rid(34)], "kg_index": [34], "field": "x_ge", "from": 1, "to": 0.2,
     "cause": "the quoted ~9 W/mK belongs to 20% Ge, not pure Ge"},
    {"op": "quarantine", "op_id": "quarantine-literature-unattributable-2026-09-29",
     "rows": [rid(i) for i in [33, 17, 18, 19, 20] + derived],
     "kg_index": [33, 17, 18, 19, 20] + derived,
     "cause": "row 33: a bulk-alloy range attributed to pure Si (true x unknown); rows 17-20: x is a dopant level; "
              + ", ".join(map(str, derived)) + ": derived arithmetic, not reported values; reversible pending verbatim re-extraction"},
]
payload = {"audit": "second-extractor-value-audit-2026-09-29",
           "evidence": "phase_c/chd/second_extractor/agreement.json",
           "extractor": "Claude claude-opus-5-5, blind to first-extractor labels"}
if "--dry-run" in sys.argv:
    print(json.dumps(ops, indent=1)); sys.exit()
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
for op in ops:
    if any(e["payload"].get("op_id") == op["op_id"] for e in led.entries):
        continue
    op = dict(op, rows_merkle_root=merkle_root(op["rows"]), **payload)
    e = led.append("shard_operation", op)
    print(op["op"], len(op["rows"]), "rows -> seq", e["seq"])
assert led.verify_chain()
