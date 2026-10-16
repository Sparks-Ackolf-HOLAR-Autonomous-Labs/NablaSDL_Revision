#!/usr/bin/env python3
"""Analyse the size-free HNEMD campaign exactly as pre-registered in
sizefree_design.json. Reads only stages committed to the ledger, only
from the committed copies under raw/. Writes analysis_sizefree.json:
per-run gates, per-point estimates, checks G_lin/G_size, rho(x, T)
against the P1 law, BTE-DFT / HNEMD ratios, the decision branch, the
replacement-law fit when that branch is taken, and prediction checks.
Written and pushed before any campaign output existed.
Run with ~/mat_theory_pilot/venv/bin/python (numpy needed for the HG-SR branch).
"""
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "production"))
sys.path.insert(0, os.path.join(MT, "phase_c", "sr_compare"))
from analyze_campaign import run_stats  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
DESIGN = json.load(open(os.path.join(HERE, "sizefree_design.json")))
CAMPAIGN = DESIGN["campaign"]
LAW = json.load(open(os.path.join(MT, "phase_c", "final_law",
                                  "final_law.json")))["bulk_law_terms"]


def law(x, T):
    return 1.0 / (LAW["1"] + LAW["x"] * x + LAW["x^2"] * x * x + LAW["T"] * T)


def bte(x, T):
    p = os.path.join(MT, "party4_bte", "results", f"bte_x{x:g}_T{T}.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    for k in ("kappa_W_mK",):
        if k in d:
            return float(d[k])
    return None


def committed():
    out = set()
    for l in open(LEDGER):
        e = json.loads(l)
        if e["kind"] == "batch_result" and e["payload"].get("campaign") == CAMPAIGN:
            out.add(e["payload"]["stage"])
    return out


def est(runs):
    ok = [r for r in runs if r["pass"]]
    if len(ok) < 2:
        return None
    v = [r["kappa"] for r in ok]
    n = len(v)
    se = max(st.stdev(v) / math.sqrt(n), math.sqrt(sum(r["sem"] ** 2 for r in ok)) / n)
    return {"kappa": round(st.mean(v), 4), "se": round(se, 4), "n": n}


def agree(a, b):
    return abs(a["kappa"] - b["kappa"]) <= (2 * math.hypot(a["se"], b["se"])
                                           + 0.10 * (a["kappa"] + b["kappa"]) / 2)


def main():
    stages = committed()
    runs = []
    for r in DESIGN["runs"]:
        if r["stage"] in stages:
            runs.append(dict(r, **run_stats(os.path.join(HERE, "raw", r["run_id"]), r)))

    def pick(check, x, T):
        return est([r for r in runs if r["check"] == check and r["x_ge"] == x
                    and r["T_K"] == T])

    pts = {}
    for r in DESIGN["runs"]:
        if r["check"] == "main":
            k = (r["x_ge"], r["T_K"])
            if k not in pts:
                e = pick("main", *k)
                if e:
                    e.update(x=k[0], T=k[1], in_law_domain=r["in_law_domain"],
                             law=round(law(*k), 4), rho=round(e["kappa"] / law(*k), 4))
                    b = bte(*k)
                    if b:
                        e.update(bte=b, bte_over_hnemd=round(b / e["kappa"], 3))
                    pts[k] = e
    checks = {}
    for x in (0.15, 0.85):
        base = pts.get((x, 300))
        lin, size = pick("linearity", x, 300), pick("size", x, 300)
        checks[f"G_lin_x{x}"] = bool(base and lin and agree(base, lin))
        checks[f"G_size_x{x}"] = bool(base and size and agree(base, size))
        checks[f"values_x{x}"] = {"base": base, "lin": lin, "size": size}
    ok300 = all(checks[f"G_{c}_x{x}"] for c in ("lin", "size") for x in (0.15, 0.85))
    use = [p for p in pts.values() if p["in_law_domain"] and (p["T"] != 300 or ok300)]
    rhos = [p["rho"] for p in use]
    out = {"campaign": CAMPAIGN, "stages_committed": sorted(stages),
           "runs": [{k: r[k] for k in ("run_id", "kappa", "sem", "drift_z",
                                       "mean_T", "gates", "pass")} for r in runs],
           "points": [pts[k] for k in sorted(pts)], "checks": checks,
           "300K_used_in_decision": ok300, "n_decision_points": len(use)}
    branch = None
    if len(stages) == 2 and rhos:
        if not ok300 and len(use) < 6:
            branch = "no_decision"
        else:
            med = st.median(rhos)
            cv = st.stdev(rhos) / st.mean(rhos) if len(rhos) > 1 else 0.0
            out.update(median_rho=round(med, 4), cv_rho=round(cv, 4))
            if 0.85 <= med <= 1.15 and all(abs(r - 1) <= 0.25 for r in rhos):
                branch = "strengthen"
            elif med > 1.15:
                branch = "correct_level" if cv <= 0.15 else "replace_level"
            elif med < 0.85:
                branch = "downweight"
            else:
                branch = "no_rule_matched"
        if branch == "replace_level":
            import hgsr2
            rows = []
            for r in runs:
                p = pts.get((r["x_ge"], r["T_K"]))
                if r["check"] == "main" and r["pass"] and p in use:
                    rows.append({"x": r["x_ge"], "T": float(r["T_K"]), "L": 0.0,
                                 "kappa": r["kappa"], "party": "HNEMD",
                                 "regime": f"x{r['x_ge']}T{r['T_K']}",
                                 "cell": f"x{r['x_ge']}T{r['T_K']}"})
            phys = hgsr2.physics_domain(x=(0.05, 0.9), T=(300.0, 1100.0))
            m = hgsr2.fit(rows, ["x", "T"], noise=True, search="beam", beam=200,
                          physics=phys)
            s = m["selected"]
            out["replacement_law"] = {"target": "r = 1/kappa",
                                      "terms": s["names"], "coefs": s["coefs"],
                                      "logo_msle": s.get("logo_msle")}
    out["decision_branch"] = branch
    if branch:
        p = {}
        p05 = pts.get((0.5, 300))
        p["Pr1"] = bool(p05 and 1.2 <= p05["rho"] <= 1.6)
        p["Pr2"] = bool(rhos and st.median(rhos) > 1.15)
        p["Pr3"] = all(min((q for q in pts.values() if q["T"] == T),
                           key=lambda q: q["kappa"])["x"] in (0.3, 0.5, 0.7)
                       for T in (300, 700, 1100))
        p["Pr4"] = all(pts[(x, 1100)]["kappa"] < pts[(x, 300)]["kappa"]
                       for x in (0.15, 0.2, 0.3, 0.5, 0.7, 0.85)
                       if (x, 1100) in pts and (x, 300) in pts) and bool(
            (0.5, 1100) in pts and (0.5, 300) in pts and
            1 - pts[(0.5, 1100)]["kappa"] / pts[(0.5, 300)]["kappa"] <= 0.30)
        p["Pr5"] = bool(p05 and "bte_over_hnemd" in p05 and 2.4 <= p05["bte_over_hnemd"] <= 3.4)
        p["Pr6"] = checks["G_lin_x0.15"] and checks["G_lin_x0.85"]
        p["Pr7"] = checks["G_size_x0.15"] and checks["G_size_x0.85"]
        out["predictions"] = p
    json.dump(out, open(os.path.join(HERE, "analysis_sizefree.json"), "w"), indent=1)
    print(json.dumps({k: out.get(k) for k in ("stages_committed", "median_rho", "cv_rho",
                                               "decision_branch", "predictions")}, indent=1))


if __name__ == "__main__":
    main()
