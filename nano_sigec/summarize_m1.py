#!/usr/bin/env python3
"""Reduce the committed M1 MACE outputs (m1/out/*.json) to m1/m1_summary.json:
gates M1a/M1b, delta_C per x, dE_prec per x, dE_site per x."""
import glob, json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "m1")
runs = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(os.path.join(OUT, "out", "*.json"))}
b = runs["bulk"]
expt = {"Si": 5.431, "Ge": 5.658, "SiC": 4.360}
m1a = {k: {"a_mace": b[k]["a_A"], "a_expt": v, "rel": b[k]["a_A"] / v - 1} for k, v in expt.items()}
S = {"M1a": {"rows": m1a, "pass": all(abs(r["rel"]) <= 0.025 for r in m1a.values()) and all(b[k]["converged"] for k in expt)}}
mu_si = b["Si"]["E_eV"] / b["Si"]["n_atoms"]
e_sic = b["SiC"]["E_eV"] / (b["SiC"]["n_atoms"] / 2)
per_x, allconv, r2ok = {}, True, True
for x in (0.0, 0.2, 0.5):
    cfg = [r for k, r in runs.items() if k != "bulk" and abs(r["x"] - x) < 1e-9]
    ys, lna, dprec, dsite = [], [], [], []
    for r in cfg:
        for q in r["runs"].values():
            allconv &= q["converged"]
        for q in r.get("site_pref", {}).values():
            allconv &= q["converged"]
        for nc in (0, 2, 4):
            q = r["runs"][f"nC{nc}"]
            ys.append(nc / r["n_sites"]); lna.append(np.log(q["a_A"]))
        e0, e1 = r["runs"]["nC0"]["E_eV"], r["runs"]["nC1"]["E_eV"]
        dprec.append(e0 + e_sic - e1 - 2 * mu_si)
        if "site_pref" in r:
            sp = r["site_pref"]
            dsite.append({"dE_site": sp["maxGe"]["E_eV"] - sp["minGe"]["E_eV"],
                          "nGe_nn_max": sp["maxGe"]["n_Ge_nn"], "nGe_nn_min": sp["minGe"]["n_Ge_nn"]})
    ys, lna = np.array(ys), np.array(lna)
    A = np.vstack([ys, np.ones_like(ys)]).T
    coef, res, *_ = np.linalg.lstsq(A, lna, rcond=None)
    pred = A @ coef
    r2 = 1 - ((lna - pred) ** 2).sum() / ((lna - lna.mean()) ** 2).sum()
    r2ok &= r2 >= 0.9
    per_x[f"{x:g}"] = {"n_configs": len(cfg), "delta_C": float(coef[0]), "R2": float(r2),
                        "a0_A": float(np.exp(coef[1])), "dE_prec_eV": dprec,
                        "dE_prec_mean_eV": float(np.mean(dprec)),
                        "site_pref": dsite,
                        "dE_site_mean_eV": float(np.mean([d["dE_site"] for d in dsite])) if dsite else None}
S["M1b"] = {"all_converged": bool(allconv), "all_R2_ge_0.9": bool(r2ok), "pass": bool(allconv and r2ok)}
S["per_x"] = per_x
S["mu_Si_eV"], S["E_SiC_fu_eV"] = mu_si, e_sic
S["modified_vegard_delta_C"] = (4.360 - 5.431) / (0.5 * 5.431)
S["gates_pass"] = S["M1a"]["pass"] and S["M1b"]["pass"]
json.dump(S, open(os.path.join(OUT, "m1_summary.json"), "w"), indent=1)
print(json.dumps({k: (v if k != "per_x" else {x: {kk: vv for kk, vv in d.items() if kk not in ("site_pref", "dE_prec_eV")} for x, d in v.items()}) for k, v in S.items()}, indent=1))
