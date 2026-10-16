#!/usr/bin/env python3
"""Analyse the 300 K level campaign exactly as pre-registered in
level300_design.json. Reads only committed copies under raw/ for stages
already on the ledger. After L1: per-run gates, the L1 points, G_lin,
G_conv and Lstar (this file is what make_runs_level300.py reads to allow
an L2 build). After L2: rho300 per composition, the branch, predictions.
Written and pushed before any run output existed.
Run with ~/mat_theory_pilot/venv/bin/python or plain python3."""
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "production"))
sys.path.insert(0, os.path.join(HERE, ".."))
from analyze_campaign import run_stats  # noqa: E402
from analyze_sizefree import est, agree, law  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
DESIGN = json.load(open(os.path.join(HERE, "level300_design.json")))
CARRIED = DESIGN["level_factor_carried"]


def committed():
    out = set()
    for l in open(LEDGER):
        e = json.loads(l)
        if e["kind"] == "batch_result" and e["payload"].get("campaign") == DESIGN["campaign"]:
            out.add(e["payload"]["stage"])
    return out


def main():
    stages = committed()
    if "L1" not in stages:
        sys.exit("L1 not on the ledger yet")
    runs = [dict(r, **run_stats(os.path.join(HERE, "raw", r["run_id"]), r))
            for r in DESIGN["runs"] if r["stage"] in stages]

    def pt(x, nx, fe, check=None):
        return est([r for r in runs if r["x_ge"] == x and r["cells"][0] == nx
                    and r["Fe_per_A"] == fe and (check is None or r["check"] == check)])

    out = {"campaign": DESIGN["campaign"], "stages_committed": sorted(stages),
           "runs": [{k: r[k] for k in ("run_id", "kappa", "sem", "drift_z", "mean_T",
                                       "gates", "pass")} for r in runs]}
    l1 = {}
    for x in (0.15, 0.85):
        l1[str(x)] = {f"{nx}x8x8_Fe5e-5": pt(x, nx, 5e-5, "size") for nx in (16, 32, 48)}
        l1[str(x)]["32x8x8_Fe2.5e-5"] = pt(x, 32, 2.5e-5, "linearity")
    out["L1_points"] = l1

    def ok(a, b):
        return bool(a and b and agree(a, b))

    g_lin = all(ok(l1[k]["32x8x8_Fe5e-5"], l1[k]["32x8x8_Fe2.5e-5"]) for k in l1)
    g_conv = all(ok(l1[k]["32x8x8_Fe5e-5"], l1[k]["48x8x8_Fe5e-5"]) for k in l1)
    lstar = None
    if g_lin and g_conv:
        lstar = 16 if all(ok(l1[k]["16x8x8_Fe5e-5"], l1[k]["48x8x8_Fe5e-5"]) for k in l1) else 32
    out.update(G_lin=g_lin, G_conv=g_conv, Lstar=lstar)
    pred = {"PrL1": all(r["gates"]["R3_no_runaway"] and r["gates"]["R4_physical"] for r in runs),
            "PrL2": all(l1[k]["16x8x8_Fe5e-5"] and l1[k]["48x8x8_Fe5e-5"] and
                        l1[k]["16x8x8_Fe5e-5"]["kappa"] < l1[k]["48x8x8_Fe5e-5"]["kappa"]
                        for k in l1),
            "PrL3": bool(g_lin and g_conv and lstar == 32)}
    branch = None
    if not (g_lin and g_conv):
        branch = "fail"
    elif f"L2-box{lstar}" in stages:
        pts = []
        for x in (0.15, 0.2, 0.3, 0.5, 0.7, 0.85):
            if x in (0.15, 0.85):
                e = l1[str(x)][f"{lstar}x8x8_Fe5e-5"]
            else:
                e = est([r for r in runs if r["x_ge"] == x and r["stage"] == f"L2-box{lstar}"])
            if e:
                e = dict(e, x=x, law=round(law(x, 300), 4), rho300=round(e["kappa"] / law(x, 300), 4))
                pts.append(e)
        out["points_300K"] = pts
        if len(pts) < 5:
            branch = "fail"
        else:
            rh = [p["rho300"] for p in pts]
            m, cv = st.median(rh), st.stdev(rh) / st.mean(rh)
            out.update(median_rho300=round(m, 4), cv_rho300=round(cv, 4),
                       m_over_carried=round(m / CARRIED, 4))
            if cv > 0.15:
                branch = "c_downweight_shape_300K"
            elif abs(m / CARRIED - 1) <= 0.10:
                branch = "a_strengthen"
            else:
                branch = "b_correct_T_dependent_level"
            pred["PrL4"] = branch == "b_correct_T_dependent_level" and m > CARRIED
    out["decision_branch"] = branch
    out["predictions"] = pred
    json.dump(out, open(os.path.join(HERE, "analysis_level300.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("stages_committed", "G_lin", "G_conv", "Lstar",
                                          "decision_branch", "predictions")}, indent=1))


if __name__ == "__main__":
    main()
