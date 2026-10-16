"""Stage-0 data access (pure python + numpy, no jax).

Party labeling follows ../assemble_evidence.py: a point from
../../pilot/kg/extracted_points.json belongs to the LITERATURE party iff
its corpusId is a Semantic Scholar corpus id (all digits). Since
assemble_evidence.py was written, derived parties landed in the same
file (BTE-DFT, MACE-MD, DB-CITRINE); they are NOT literature rows and
are excluded here by the same digits rule (the committed
evidence_table.json predates them and has exactly these 67 rows).

MD contrast party: the CHPC-MD finite-size rows (snippet_hash like
x0.5_T300_z48_s202_a4_w50 carries composition, temperature, box length
in cells, seed, cross-section and swap interval). The 4 DGX-MD rows do
not carry seed/size in a parseable form and are dropped (documented).

Every row gets a stable id = ledger.leaf_hash(raw point dict), because
snippet_hash is per snippet (20 distinct over 67 literature rows), not
per row.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.normpath(os.path.join(HERE, "..", ".."))
KG = os.path.join(MT, "pilot", "kg", "extracted_points.json")
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import leaf_hash  # noqa: E402

# Pre-declared class groupings (small raw classes merged by physics,
# not by outcome): boundary-scattering-dominated samples form one group.
SAMPLE_GROUP = {"bulk": "bulk",
                "nanowire": "reduced-dim", "nanostructured": "reduced-dim",
                "film": "reduced-dim", "superlattice": "reduced-dim",
                "amorphous": "amorphous",
                "other": "unclassified"}
METHOD_GROUP = {"MD": "simulation", "BTE/DFT": "simulation",
                "experiment": "measurement", "model-fit": "measurement",
                "unclear": "unclear"}


def literature_rows():
    raw = json.load(open(KG))
    out = []
    for p in raw:
        if not str(p.get("corpusId")).isdigit():
            continue
        out.append({
            "row_id": leaf_hash(p),
            "x": p.get("x_ge"), "T": p.get("T_K"), "kappa": p.get("kappa_W_mK"),
            "system": p.get("system"), "method": p.get("method"),
            "sample_group": SAMPLE_GROUP.get(p.get("system"), "unclassified"),
            "method_group": METHOD_GROUP.get(p.get("method"), "unclear"),
            "corpusId": str(p.get("corpusId")),
            "snippet_hash": p.get("snippet_hash"),
            "title": p.get("title"),
        })
    return out


def md_rows():
    raw = json.load(open(KG))
    out, dropped = [], []
    for p in raw:
        cid = str(p.get("corpusId"))
        if cid not in ("CHPC-MD", "DGX-MD"):
            continue
        m = re.match(r"x([\d.]+)_T(\d+)_z(\d+)_s(\d+)(?:_a(\d+)_w(\d+))?$",
                     p["snippet_hash"])
        if not m:
            dropped.append({"party": cid, "snippet_hash": p["snippet_hash"]})
            continue
        x = float(p["x_ge"])
        ncz = int(m.group(3))
        a_lat = 5.431 + (5.658 - 5.431) * x          # Vegard, Angstrom
        out.append({
            "row_id": leaf_hash(p), "party": cid,
            "x": x, "T": float(p["T_K"]), "kappa": float(p["kappa_W_mK"]),
            "ncz": ncz, "L": ncz * a_lat, "seed": int(m.group(4)),
            "xsec": int(m.group(5) or 4), "swap": int(m.group(6) or 50),
            "snippet_hash": p["snippet_hash"],
        })
    return out, dropped
