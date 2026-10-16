#!/usr/bin/env python3
"""Leg-level reading of the SiGeC recipe: combine the 300 K and 1100 K picks
(and the 500, 700, 900 K points the same model carries) into the quantity a
thermoelectric leg actually conducts. Derived reporting from the committed
model after the r30 decision (ledger 105); POST HOC, no ledger decision.

For a leg of constant cross-section between a cold end Tc and a hot end Th,
the conductive heat leak is (A/L) * integral of kappa dT (Kirchhoff
transform), so the leg is ranked by the temperature-averaged kappa
kbar = integral(kappa dT) / (Th - Tc), here by the trapezoid rule on
300, 500, 700, 900, 1100 K. Output: leg_level.json."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
NS = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NS, "radius_contrast"))
import fit_radius_contrast as FR  # noqa: E402

r = json.load(open(os.path.join(NS, "small_sic", "r30", "r30_results.json")))
lx = np.log([c[0] for c in r["measured_curve"]]); ly = np.log([c[1] for c in r["measured_curve"]])


def lamfun(Rn):  # same rule as analyze_r30.py and p1_numbers.py
    if Rn <= 3.0:
        return float(np.exp(np.interp(np.log(Rn), lx, ly)))
    s = min(0.0, (ly[-1] - ly[-2]) / (lx[-1] - lx[-2]))
    return float(np.exp(ly[-1] + s * (np.log(Rn) - lx[-1])))


TS = [300, 500, 700, 900, 1100]
S = FR.S


def k(x, T, y, Rm):
    return FR.kC(x, T, y, Rm, lamfun(Rm * 1e9))


def kbar(vals):
    return float(np.trapezoid(vals, TS) / (TS[-1] - TS[0]))


grid = [(x, y, Rm) for x in S.XS for y in S.YS for Rm in (S.RS if y > 0 else [S.RS[0]])]
tab = {g: [k(*g[:1], T, *g[1:]) for T in TS] for g in grid}
out = {"status": "POST HOC derived reporting; model = committed SiGeC kappa model with the ledger-105 measured small-SiC curve, D_eff = 0.3 um",
       "temperatures_K": TS}
# 1. pick at each temperature
out["pick_per_T"] = {}
for i, T in enumerate(TS):
    g = min(grid, key=lambda g: tab[g][i])
    out["pick_per_T"][str(T)] = {"x": g[0], "y_C": g[1], "R_nm": g[2] * 1e9, "kappa": tab[g][i]}
# 2. pick for a 300-1100 K leg
g = min(grid, key=lambda g: kbar(tab[g]))
out["pick_leg"] = {"x": g[0], "y_C": g[1], "R_nm": g[2] * 1e9, "kbar": kbar(tab[g])}
# 3. recipe family y = 3 at% C as 2.5 nm SiC: kbar versus Ge content, and carbon-free reference
fam = {}
for x in S.XS:
    kc = [k(x, T, 0.03, 2.5e-9) for T in TS]
    k0 = [k(x, T, 0.0, 2.5e-9) for T in TS]
    fam[f"{x:g}"] = {"kbar_C3_R2.5": kbar(kc), "kbar_noC": kbar(k0), "kappa_C3_R2.5": dict(zip(map(str, TS), kc))}
out["by_x_C3_R2.5"] = fam
best = min(fam.values(), key=lambda v: v["kbar_C3_R2.5"])["kbar_C3_R2.5"]
out["penalty_pct_vs_best_leg"] = {x: 100 * (v["kbar_C3_R2.5"] / best - 1) for x, v in fam.items()}
# 4. graded leg: each 200 K segment takes the best x of its two end temperatures
seg = []
for i in range(len(TS) - 1):
    xs_best = min(S.XS, key=lambda x: k(x, TS[i], 0.03, 2.5e-9) + k(x, TS[i + 1], 0.03, 2.5e-9))
    seg.append({"T_lo": TS[i], "T_hi": TS[i + 1], "x": xs_best,
                "kbar_seg": (k(xs_best, TS[i], 0.03, 2.5e-9) + k(xs_best, TS[i + 1], 0.03, 2.5e-9)) / 2})
out["graded_leg"] = {"segments": seg, "kbar": float(np.mean([s["kbar_seg"] for s in seg])),
                     "gain_pct_vs_best_uniform": 100 * (1 - np.mean([s["kbar_seg"] for s in seg]) / best)}
# 5. Ge needed: lowest x whose carbon recipe leg-average matches carbon-free Si0.8Ge0.2 at the same grains
ref = fam["0.2"]["kbar_noC"]
xs_ok = [x for x in S.XS if fam[f"{x:g}"]["kbar_C3_R2.5"] <= ref]
out["leg_ge_saving"] = {"reference_noC_x0.2_kbar": ref, "lowest_x_grid_matching": min(xs_ok) if xs_ok else None}
# 6. leg-level Ge saving at 1 and 3 at% C (2.5 and 5 nm SiC), x interpolated linearly on the grid
sav = {}
for y in (0.01, 0.03):
    for Rm in (2.5e-9, 5e-9):
        kb = [kbar([k(x, T, y, Rm) for T in TS]) for x in S.XS]
        xm = S.xmin_for(kb, ref)
        sav[f"y{y:g}_R{Rm*1e9:g}"] = None if xm is None else {"x_match": xm, "ge_saving_pct": 100 * (1 - xm / 0.2)}
out["leg_ge_saving"]["interpolated"] = sav
json.dump(out, open(os.path.join(HERE, "leg_level.json"), "w"), indent=1)
print(json.dumps({k_: v for k_, v in out.items() if k_ != "by_x_C3_R2.5"}, indent=1))
for x, v in fam.items():
    print(x, round(v["kbar_C3_R2.5"], 3), round(v["kbar_noC"], 3), {T: round(q, 3) for T, q in v["kappa_C3_R2.5"].items()})
