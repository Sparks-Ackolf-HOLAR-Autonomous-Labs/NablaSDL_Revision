#!/usr/bin/env python3
"""Figure for the SiGeC campaign. Since the M1c converged rerun (ledger seq 53-55) it reads
results/sigec_results_m1c.json and m1c/m1c_summary.json (the validated MACE values)."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(os.path.join(HERE, "results", "sigec_results_m1c.json")))
m1 = json.load(open(os.path.join(HERE, "m1c", "m1c_summary.json")))
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))
# (a) kappa_L vs carbon content, x=0.2, 300 K, d_eff = 0.3 um
sel = [q for q in r["D1"] if q["x"] == 0.2 and q["T"] == 300 and q["d_m"] == 0.3e-6]
k0 = sel[0]["kappa_noC"]
styles = [("sub_eps0", "substitutional C, mass only", "C4", ":"),
          ("sub_eps39", "substitutional C, strain upper bound", "C0", "-"),
          ("SiC_R2.5nm_stiffness", "SiC particles, R = 2.5 nm", "C3", "-"),
          ("SiC_R10nm_stiffness", "SiC particles, R = 10 nm", "C1", "-"),
          ("SiC_R100nm_stiffness", "SiC particles, R = 100 nm", "C7", "-")]
for key, lab, c, ls in styles:
    pts = sorted((q["y_C"], q["kappa"]) for q in sel if q["form"] == key)
    ax[0].plot([0] + [p[0] * 100 for p in pts], [k0] + [p[1] for p in pts], ls, color=c, marker="o", ms=3, label=lab)
ax[0].set_xlabel("carbon content (at%)"); ax[0].set_ylabel("lattice kappa (W/mK)")
ax[0].set_title("(a) Si0.8Ge0.2, 300 K, effective grain 0.3 um"); ax[0].legend(fontsize=7)
# (b) carbon-for-germanium frontier
for key, lab, c, ls in styles:
    row = sorted((q["y_C"], q["x_min"]) for q in r["D2_frontier"] if q["T"] == 300 and q["d_m"] == 0.3e-6
                 and q["target"] == 2.5 and q["form"] == key and q["x_min"] is not None)
    base = [q["x_min"] for q in r["D2_frontier"] if q["T"] == 300 and q["d_m"] == 0.3e-6 and q["target"] == 2.5 and q["form"] == "none"]
    if row:
        ax[1].plot([0] + [p[0] * 100 for p in row], base + [p[1] for p in row], ls, color=c, marker="o", ms=3, label=lab)
ax[1].axhline(0.2, color="gray", lw=0.8); ax[1].text(0.05, 0.205, "RTG alloy x = 0.2", fontsize=8, color="gray")
ax[1].set_xlabel("carbon content (at%)"); ax[1].set_ylabel("minimum Ge fraction for kappa_L <= 2.5 W/mK")
ax[1].set_title("(b) Ge needed for kappa_L <= 2.5 (carbon-free: never below 2.70)"); ax[1].legend(fontsize=7)
# (c) where carbon goes (MACE)
xs = [0, 0.2, 0.5]
ax[2].plot(xs, [m1["per_x"][f"{x:g}"]["dE_prec_mean_eV"] for x in xs], "o-", color="C3", label="C leaves lattice to form SiC (dE_prec)")
ds = [m1["per_x"][f"{x:g}"]["dE_site_mean_eV"] for x in xs[1:]]
ax[2].plot(xs[1:], ds, "s--", color="C0", label="C next to Ge minus next to Si (dE_site)")
ax[2].axhline(0, color="gray", lw=0.8)
ax[2].set_xlabel("host Ge fraction x"); ax[2].set_ylabel("energy per C (eV)")
ax[2].set_title("(c) where carbon goes (MACE-MP-0, converged)"); ax[2].legend(fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "results", "fig_sigec.png"), dpi=140)
print("ok")
