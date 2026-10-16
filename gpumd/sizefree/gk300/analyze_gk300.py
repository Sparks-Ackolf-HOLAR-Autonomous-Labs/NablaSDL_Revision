#!/usr/bin/env python3
"""Analyse the 300 K Green-Kubo campaign exactly as pre-registered in
gk300_design.json. Reads only committed copies under raw/ for stages already
on the ledger. After K1: run gates, K1 points, G_plat, G_meth, G_conv and
box* (make_runs_gk300.py reads box* before it allows a K2 build). After K2:
rho300 per composition, the branch, predictions. Written and pushed before
any run output existed. Output: analysis_gk300.json."""
import hashlib
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
reg = open(os.path.join(HERE, "PREREGISTERED_SHA256")).read().split()[0]
if hashlib.sha256(open(os.path.join(HERE, "gk300_design.json"), "rb").read()).hexdigest() != reg:
    sys.exit("gk300_design.json changed after registration")
D = json.load(open(os.path.join(HERE, "gk300_design.json")))
CARRIED = D["level_factor_carried"]
REF = D["hnemd_reference_700K"]


def law(x, T):
    return 1.0 / (0.2092492 + 1.9190900 * x - 2.2443438 * x * x + 8.352241e-5 * T)


def agree(a, sa, b, sb):
    return abs(a - b) <= 2 * math.sqrt(sa ** 2 + sb ** 2) + 0.10 * (a + b) / 2


def committed():
    out = set()
    for l in open(LEDGER):
        e = json.loads(l)
        if e["kind"] == "batch_result" and e["payload"].get("campaign") == D["campaign"]:
            out.add(e["payload"]["stage"])
    return out


def run_stats(r):
    d = os.path.join(HERE, "raw", r["run_id"])
    s = {"run_id": r["run_id"], "gates": {}}
    ex = open(os.path.join(d, "exit_status")).read().strip() if os.path.exists(os.path.join(d, "exit_status")) else "missing"
    rows = []
    if os.path.exists(os.path.join(d, "hac.out")):
        rows = [[float(v) for v in l.split()] for l in open(os.path.join(d, "hac.out")) if l.strip()]
    s["gates"]["R1"] = ex == "0" and len(rows) == r["hac"]["Nc"] // r["hac"]["output_interval"]
    Ts = [float(l.split()[0]) for l in open(os.path.join(d, "thermo.out")) if l.strip() and not l.lstrip().startswith("#")] if os.path.exists(os.path.join(d, "thermo.out")) else []
    s["mean_T"] = st.mean(Ts) if Ts else None
    s["gates"]["R2"] = bool(Ts) and abs(s["mean_T"] - r["T_K"]) <= 0.03 * r["T_K"]
    if rows:
        t = [w[0] for w in rows]
        krun = [(w[6] + w[7] + w[8] + w[9] + w[10]) / 3 for w in rows]  # (kx + ky + kz) / 3
        def win(a, b):
            v = [k for tt, k in zip(t, krun) if a <= tt <= b]
            return st.mean(v) if v else float("nan")
        s["kappa"], s["k_50_75"], s["k_75_100"], s["k_25_50"] = win(50, 100), win(50, 75), win(75, 100), win(25, 50)
        s["kappa_dir_50_100"] = [st.mean([(w[6] + w[7]) for w in rows if 50 <= w[0] <= 100]),
                                 st.mean([(w[8] + w[9]) for w in rows if 50 <= w[0] <= 100]),
                                 st.mean([w[10] for w in rows if 50 <= w[0] <= 100])]
    else:
        s["kappa"] = None
    s["gates"]["R3"] = s["kappa"] is not None and math.isfinite(s["kappa"]) and 0 < s["kappa"] < 2000
    s["pass"] = all(s["gates"].values())
    return s


def point(stats, key="kappa", min_n=3):
    v = [s[key] for s in stats if s["pass"]]
    if len(v) < min_n:
        return None
    return {"kappa": st.mean(v), "se": st.stdev(v) / math.sqrt(len(v)), "n": len(v)}


def main():
    stages = committed()
    if "K1" not in stages:
        sys.exit("K1 not on the ledger yet")
    rows = [r for r in D["runs"] if r["stage"] in stages]
    stats = {r["run_id"]: run_stats(r) for r in rows}
    out = {"design_sha256": reg, "stages": sorted(stages), "runs": list(stats.values()), "points": {}}

    def pts(x, T, box, stage):
        sel = [stats[r["run_id"]] for r in rows if r["x_ge"] == x and r["T_K"] == T and r["cells"][0] == box and r["stage"] == stage]
        mn = 2 if box == 16 else 3
        return {k: point(sel, k, mn) for k in ("kappa", "k_50_75", "k_75_100", "k_25_50")}

    K1 = {}
    for x in (0.15, 0.85):
        for b in (8, 12, 16):
            K1[(x, 300, b)] = pts(x, 300, b, "K1")
    K1[(0.5, 700, 8)] = pts(0.5, 700, 8, "K1")
    out["points"]["K1"] = {f"x{x:g}_T{T}_{b}c": v for (x, T, b), v in K1.items()}
    plat = {}
    for k, v in K1.items():
        a, b = v["k_50_75"], v["k_75_100"]
        plat[f"x{k[0]:g}_T{k[1]}_{k[2]}c"] = bool(a and b and agree(a["kappa"], a["se"], b["kappa"], b["se"]))
    G_plat = all(plat.values())
    m = K1[(0.5, 700, 8)]["kappa"]
    G_meth = bool(m) and agree(m["kappa"], m["se"], REF["kappa"], REF["se"])

    def ag(x, b1, b2):
        p, q = K1[(x, 300, b1)]["kappa"], K1[(x, 300, b2)]["kappa"]
        return bool(p and q) and agree(p["kappa"], p["se"], q["kappa"], q["se"])

    G_conv = all(ag(x, 12, 16) for x in (0.15, 0.85))
    box = None
    if G_plat and G_meth and G_conv:
        box = 8 if all(ag(x, 8, 16) for x in (0.15, 0.85)) else 12
    out.update({"G_plat": {"per_point": plat, "pass": G_plat}, "G_meth": {"gk": m, "hnemd": REF, "pass": G_meth},
                "G_conv": G_conv, "box_star": box})
    branch = "fail" if box is None else None
    rho = {}
    if box is not None and f"K2-box{box}" in stages:
        for x in (0.15, 0.2, 0.3, 0.5, 0.7, 0.85):
            p = K1[(x, 300, box)]["kappa"] if x in (0.15, 0.85) else pts(x, 300, box, f"K2-box{box}")["kappa"]
            if p:
                rho[f"{x:g}"] = p["kappa"] / law(x, 300)
                out["points"].setdefault("K2", {})[f"x{x:g}_T300_{box}c"] = p
        if len(rho) < 5:
            branch = "fail"
        else:
            mm, cv = st.median(rho.values()), st.stdev(rho.values()) / st.mean(rho.values())
            out["median_rho300"], out["cv_rho300"] = mm, cv
            if cv > 0.15:
                branch = "c_downweight_shape_300K"
            elif abs(mm / CARRIED - 1) <= 0.10:
                branch = "a_strengthen"
            else:
                branch = "b_correct_T_dependent_level"
    out["rho300"] = rho
    out["decision_branch"] = branch
    k15 = K1[(0.15, 300, box)]["kappa"] if box else None
    out["predictions"] = {"PrK1": G_meth, "PrK2": G_plat and G_conv and box == 12,
                          "PrK3": bool(k15) and k15["kappa"] >= 4.60,
                          "PrK4": branch == "b_correct_T_dependent_level" and out.get("median_rho300", 0) > CARRIED}
    json.dump(out, open(os.path.join(HERE, "analysis_gk300.json"), "w"), indent=1, sort_keys=True, default=float)
    print(json.dumps({k: out[k] for k in ("box_star", "decision_branch", "predictions")}, default=float))


if __name__ == "__main__":
    main()
