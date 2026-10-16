#!/usr/bin/env python3
"""Paper 1's materials deliverable: the kappa(x, T) alloy law for
Tersoff-1989 Si1-xGex, fitted by HG-SR on the post-operation evidence
state of the CHPC-MD party, with its validity domain, and compared with
the other method families (BTE-DFT, MACE-MD) and experiment (DB-CITRINE).

Evidence state (every exclusion is a ledgered operation or a declared
domain rule, never a post-hoc choice):
  - Phase B + follow-up rNEMD rows at the standard protocol (ncxy 4,
    swap 50), x in [0.05, 0.95] (scope-limit, ledger seq 0)
  - production coverage batch C00-C39 (ledger seq 3, 9-13); the four
    physics probes are out: N0/N1 near melting (scope-limited by the
    physics guard), N2/N3 amorphous (split: another phase, structural
    evidence in production/results/structure_check.json)
  - the Ge-rich corner handled exactly as the pre-registered shard
    action decided (shard_action_corner/decision.json)
  - validity domain in T: T <= 0.85 T_solidus(x) (the premelting bound the
    blind fault catalog used; rows above it are excluded and counted)
Model, two stages: (A) per-series 1/L extrapolation to bulk; (B) HG-SR
(phase_c/sr_compare/hgsr.py) on the bulk rows over (x, T), regime-balanced,
with leave-one-hyperedge-out provenance. The one-stage alternative (HG-SR
on per-run rows with an L feature) is reported as an ablation.
Usage: ~/mat_theory_pilot/venv/bin/python fit_final_law.py
"""
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, ".."))
MT = os.path.abspath(os.path.join(PC, ".."))
sys.path.insert(0, os.path.join(PC, "sr_compare"))
sys.path.insert(0, os.path.join(PC, "production"))
import hgsr  # noqa: E402
from detector import regime, solidus  # noqa: E402

rows, excluded = [], {"premelting": [], "corner": [], "endpoint": []}


def k_of(j):
    return j.get("kappa_W_mK_full") or j["kappa_W_mK"]


def add(j, rid, source):
    x, T = float(j["x"]), float(j["T"])
    if x < 0.05 or x > 0.95:
        excluded["endpoint"].append(rid); return
    if T > 0.85 * solidus(x):
        excluded["premelting"].append(rid); return
    rows.append({"run_id": rid, "source": source, "x": x, "T": T,
                 "L": j["box_A"][2] / 10.0, "kappa": k_of(j),
                 "regime": regime(x, T), "party": "CHPC-MD"})


for f in sorted(glob.glob(os.path.join(MT, "chpc", "results", "x*.json"))):
    rid = os.path.basename(f)[:-5]
    j = json.load(open(f))
    if j.get("ncxy", 4) != 4 or j.get("swap_every", 50) != 50:
        continue
    add(j, rid, "phaseB")

dec = json.load(open(os.path.join(PC, "shard_action_corner", "decision.json")))
corner_ops = dec["decisions"]
x_max = 0.95
for f in sorted(glob.glob(os.path.join(PC, "production", "results", "C*_z*.json"))):
    rid = os.path.basename(f)[:-5]
    base = rid.split("_")[0]
    if base in corner_ops and corner_ops[base] != "replace" and corner_ops[base] != "keep quarantine":
        pass  # scope decisions applied below via x_max
    elif base in corner_ops:
        excluded["corner"].append(rid); continue  # replaced or still quarantined
    add(json.load(open(f)), rid, "production")
if any(op.startswith("scope-limit") for op in corner_ops.values()):
    x_max = 0.90
for f in sorted(glob.glob(os.path.join(PC, "shard_action_corner", "results", "*.json"))):
    rid = os.path.basename(f)[:-5]
    if rid == "manifest":
        continue
    base = rid[:3]
    if base in corner_ops and corner_ops[base] == "keep quarantine":
        excluded["corner"].append(rid); continue
    add(json.load(open(f)), rid, "shard-action")
in_scope = [r for r in rows if r["x"] <= x_max + 1e-9]
excluded["corner"] += [r["run_id"] for r in rows if r["x"] > x_max + 1e-9]
# Stage A (physics): per series (same x, T, seed/source), least squares
# 1/kappa = a + b/L over its box lengths, kappa_inf = 1/a. The size effect
# depends strongly on composition (b/a from about 25 mid-alloy to 70 near
# the Ge end), so it is removed per series rather than by one global 1/L
# term (the one-stage HG-SR ablation below shows why).
series = {}
for r in in_scope:
    base = re.sub(r"_z\d+", "", r["run_id"])
    series.setdefault((round(r["x"], 4), r["T"], base), []).append(r)
bulk_rows = []
for (x, T, base), rs in sorted(series.items()):
    Ls = sorted({r["L"] for r in rs})
    if len(Ls) < 2:
        continue
    b1, a = np.polyfit([1 / r["L"] for r in rs], [1 / r["kappa"] for r in rs], 1)
    if a <= 0:
        continue
    bulk_rows.append({"run_id": base, "x": x, "T": T, "L": 1e9, "kappa": 1 / a,
                      "b_over_a": b1 / a, "n_sizes": len(Ls),
                      "regime": regime(x, T), "party": "CHPC-MD"})
# Stage B (law): HG-SR on the bulk rows, features (x, T), regime-balanced.
feats = ["x", "T"]
prov = hgsr.provenance(bulk_rows, feats)
sel = prov["selected"]
bulk_terms = dict(zip(sel["names"], sel["coefs"]))
basis = {b[0]: b[2] for b in hgsr.make_basis(feats)}


def bulk_kappa(x, T):
    d = {"x": np.atleast_1d(float(x)), "T": np.atleast_1d(float(T))}
    r = sum(c * basis[n](d) for n, c in bulk_terms.items())
    return float(1.0 / r[0]) if r[0] > 0 else None


# One-stage ablation: HG-SR on per-run rows with (x, T, L) features.
one = hgsr.fit(in_scope, ["x", "T", "L"])["selected"]
b3 = {b[0]: b[2] for b in hgsr.make_basis(["x", "T", "L"])}
one_bulk = {n: c for n, c in zip(one["names"], one["coefs"]) if "/L" not in n}


def one_kappa(x, T):
    d = {"x": np.atleast_1d(float(x)), "T": np.atleast_1d(float(T)), "L": np.atleast_1d(1e9)}
    r = sum(c * b3[n](d) for n, c in one_bulk.items())
    return float(1.0 / r[0]) if r[0] > 0 else None


def med_err(fn):
    e = [abs(fn(p["x"], p["T"]) / p["kappa"] - 1) for p in bulk_rows if fn(p["x"], p["T"])]
    return float(np.median(e))


# leave-one-regime-out CV of stage B on kappa (median abs percentage error)
cv = []
for reg in sorted({p["regime"] for p in bulk_rows}):
    tr = [p for p in bulk_rows if p["regime"] != reg]
    te = [p for p in bulk_rows if p["regime"] == reg]
    m = hgsr.fit(tr, feats)["selected"]
    for p in te:
        d = {"x": np.array([p["x"]]), "T": np.array([p["T"]])}
        r = sum(c * basis[n](d) for n, c in zip(m["names"], m["coefs"]))[0]
        cv.append(abs((1 / r) / p["kappa"] - 1) * 100 if r > 0 else 100.0)


# comparison parties
kg = json.load(open(os.path.join(MT, "pilot", "kg", "extracted_points.json")))
comp = {"BTE-DFT": [], "DB-CITRINE": [], "MACE-MD": []}
for q in kg:
    cid = str(q.get("corpusId"))
    for name in comp:
        if name in cid and q.get("x_ge") is not None and q.get("T_K"):
            x, T = float(q["x_ge"]), float(q["T_K"])
            if 0.05 <= x <= x_max and T <= 0.85 * solidus(x):
                comp[name].append({"x": x, "T": T, "kappa": q["kappa_W_mK"],
                                   "law_bulk": bulk_kappa(x, T)})
for name, lst in comp.items():
    rat = [p["kappa"] / p["law_bulk"] for p in lst if p["law_bulk"]]
    comp[name] = {"points": lst, "ratio_other_over_law":
                  {"median": float(np.median(rat)) if rat else None,
                   "min": float(min(rat)) if rat else None,
                   "max": float(max(rat)) if rat else None, "n": len(rat)}}
# shape check: kappa(x)/kappa(0.5) at 300 K from the law vs the BTE party
shape = {}
for x in (0.15, 0.2, 0.5, 0.85):
    if x <= x_max:
        shape[str(x)] = bulk_kappa(x, 300) / bulk_kappa(0.5, 300)
out = {"n_runs": len(in_scope), "n_bulk_series": len(bulk_rows),
       "n_regimes": len(prov["covered_regimes"]),
       "stageB_median_abs_err_vs_series": med_err(bulk_kappa),
       "stageB_leave_one_regime_out_cv_medape_pct": float(np.median(cv)),
       "one_stage_ablation": {"selected": one, "bulk_terms": one_bulk,
                              "median_abs_err_vs_series": med_err(one_kappa)},
       "bulk_rows": bulk_rows,
       "x_max": x_max, "corner_decisions": corner_ops, "excluded": excluded,
       "selected": sel, "term_labels": prov["term_labels"],
       "blast_radius": prov["blast_radius"],
       "bulk_law_terms": bulk_terms,
       "bulk_kappa_grid": {f"x{x}_T{T}": bulk_kappa(x, T) for x in (0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9)
                           for T in (300, 700, 1100) if x <= x_max and T <= 0.85 * solidus(x)},
       "shape_kappa_over_kappa_x05_300K": shape,
       "comparison": comp,
       "validity_domain": {"x": [0.05, x_max], "T_K": "300 <= T <= 0.85 T_solidus(x)",
                           "phase": "crystalline diamond-structure random alloy",
                           "potential": "Tersoff 1989 (Si(D), Ge); absolute scale carries the measured Tersoff alloy bias"}}
json.dump(out, open(os.path.join(HERE, "final_law.json"), "w"), indent=1, default=float)
print(json.dumps({k: out[k] for k in ("n_runs", "n_bulk_series", "n_regimes", "x_max", "bulk_law_terms",
                                      "term_labels", "blast_radius", "stageB_median_abs_err_vs_series",
                                      "stageB_leave_one_regime_out_cv_medape_pct",
                                      "shape_kappa_over_kappa_x05_300K", "bulk_kappa_grid")}, indent=1, default=float))
print("one-stage ablation", one["names"], "median err", out["one_stage_ablation"]["median_abs_err_vs_series"])
for n, c in comp.items():
    print(n, c["ratio_other_over_law"])
