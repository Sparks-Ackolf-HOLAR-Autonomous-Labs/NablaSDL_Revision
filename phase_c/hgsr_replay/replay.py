#!/usr/bin/env python3
"""HG-SR replay along the campaign: refit the kappa(x, T) law on the
evidence state that held after each ledger decision, and record the law
HG-SR selects, its per-term labels (multi-supported / regime-sensitive /
scope:<party>), its blast radius, and the validity domain in force.

The final stage must reproduce phase_c/final_law/final_law.json exactly;
the script asserts it. Earlier stages reuse the same two-stage model
(per-series 1/L extrapolation, then HG-SR on bulk rows over (x, T)); a
stage with fewer than N_MIN bulk series gets HG-SR's refusal, as in
fit_party.py. No new evidence, no ledger entry: this is a reading of the
committed ledger, written for the P1 figure.
Usage: ~/mat_theory_pilot/venv/bin/python replay.py"""
import glob, json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, ".."))
MT = os.path.abspath(os.path.join(PC, ".."))
sys.path.insert(0, os.path.join(PC, "sr_compare"))
sys.path.insert(0, os.path.join(PC, "production"))
import hgsr  # noqa: E402
from detector import regime, solidus  # noqa: E402

N_MIN = 4   # bulk series below which the stage-B fit is refused (4 terms max)


def k_of(j):
    return j.get("kappa_W_mK_full") or j["kappa_W_mK"]


def row(j, rid, source):
    x, T = float(j["x"]), float(j["T"])
    return {"run_id": rid, "source": source, "x": x, "T": T,
            "L": j["box_A"][2] / 10.0, "kappa": k_of(j),
            "regime": regime(x, T), "party": "CHPC-MD"}


pool = []
for f in sorted(glob.glob(os.path.join(MT, "chpc", "results", "x*.json"))):
    rid = os.path.basename(f)[:-5]
    j = json.load(open(f))
    if j.get("ncxy", 4) != 4 or j.get("swap_every", 50) != 50:
        continue
    pool.append(row(j, rid, "phaseB" if "_a" not in rid else "followup"))
for f in sorted(glob.glob(os.path.join(PC, "production", "results", "C*_z*.json"))):
    pool.append(row(json.load(open(f)), os.path.basename(f)[:-5], "production"))
for f in sorted(glob.glob(os.path.join(PC, "shard_action_corner", "results", "*.json"))):
    rid = os.path.basename(f)[:-5]
    if rid != "manifest":
        pool.append(row(json.load(open(f)), rid, "shard-action"))
QUAR = {"C37", "C38"}   # quarantined by the frozen detector, released at seq 29

# stage: (id, label, ledger seqs, sources admitted, x range, premelt guard, quarantine active)
STAGES = [
    ("R1", "Phase B core array", "-", {"phaseB"}, (0.0, 1.0), False, False),
    ("R2", "+ seed and size follow-ups", "-", {"phaseB", "followup"}, (0.0, 1.0), False, False),
    ("R3", "scope-limit to alloys", "0", {"phaseB", "followup"}, (0.05, 0.95), False, False),
    ("R4", "+ production batch; probes scope-limited or split; Ge corner quarantined",
     "3-14", {"phaseB", "followup", "production"}, (0.05, 0.95), True, True),
    ("R5", "shard action on the Ge corner: release + scope-limit x<=0.90",
     "19, 26-29", {"phaseB", "followup", "production", "shard-action"}, (0.05, 0.90), True, False),
]


def law_str(names, coefs):
    def term(n):
        return {"1": "", "T": "T", "x*T": "xT", "x(1-x)*T": "x(1-x)T"}.get(n, n)
    s = " ".join(f"{'+' if c >= 0 else '-'} {abs(c):.3g}{('·' + term(n)) if term(n) else ''}"
                 for n, c in zip(names, coefs))
    return "1/κ = " + s.lstrip("+ ")


out = []
for sid, label, seqs, srcs, (x0, x1), guard, quar in STAGES:
    rows = []
    for r in pool:
        if r["source"] not in srcs or not (x0 - 1e-9 <= r["x"] <= x1 + 1e-9):
            continue
        if guard and r["T"] > 0.85 * solidus(r["x"]):
            continue
        if quar and r["run_id"].split("_")[0] in QUAR:
            continue
        rows.append(r)
    series = {}
    for r in rows:
        base = re.sub(r"_z\d+", "", r["run_id"])
        series.setdefault((round(r["x"], 4), r["T"], base), []).append(r)
    bulk = []
    for (x, T, base), rs in sorted(series.items()):
        if len({r["L"] for r in rs}) < 2:
            continue
        b1, a = np.polyfit([1 / r["L"] for r in rs], [1 / r["kappa"] for r in rs], 1)
        if a <= 0:
            continue
        bulk.append({"run_id": base, "x": x, "T": T, "L": 1e9, "kappa": 1 / a,
                     "regime": regime(x, T), "party": "CHPC-MD"})
    st = {"stage": sid, "label": label, "ledger_seq": seqs, "n_runs": len(rows),
          "n_bulk_series": len(bulk), "x_range": [x0, x1],
          "n_regimes": len({b["regime"] for b in bulk}),
          "excluded_nonpositive_intercept": len(series) - len(bulk) -
          sum(1 for rs in series.values() if len({r["L"] for r in rs}) < 2)}
    if len(bulk) < N_MIN:
        st["refused"] = f"{len(bulk)} bulk series < {N_MIN}"
    else:
        p = hgsr.provenance(bulk, ["x", "T"])
        sel = p["selected"]
        st.update({"terms": sel["names"], "coefs": sel["coefs"],
                   "law": law_str(sel["names"], sel["coefs"]),
                   "term_labels": p["term_labels"], "blast_radius": p["blast_radius"]})
        basis = {b[0]: b[2] for b in hgsr.make_basis(["x", "T"])}
        d = {"x": np.array([0.5]), "T": np.array([300.0])}
        r5 = sum(c * basis[n](d) for n, c in zip(sel["names"], sel["coefs"]))[0]
        st["kappa_x0.5_300K"] = float(1 / r5) if r5 > 0 else None
    out.append(st)
    print(sid, st.get("law", st.get("refused")), st.get("term_labels"))

ref = json.load(open(os.path.join(PC, "final_law", "final_law.json")))
assert out[-1]["terms"] == ref["selected"]["names"], (out[-1]["terms"], ref["selected"]["names"])
assert np.allclose(out[-1]["coefs"], ref["selected"]["coefs"], rtol=1e-10), "final stage != final_law.json"
json.dump({"note": "replay of committed evidence states; final stage asserted equal to final_law.json",
           "stages": out}, open(os.path.join(HERE, "replay.json"), "w"), indent=1)
