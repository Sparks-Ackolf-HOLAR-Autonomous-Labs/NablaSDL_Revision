#!/usr/bin/env python3
"""Bond-angle figure from bad_results.json (four panels, 7 in wide)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "bad_results.json")))
TET = R["tetrahedral_deg"]; b = np.array(R["bins_deg"]); mid = 0.5 * (b[1:] + b[:-1])
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 6.5,
                     "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(2, 2, figsize=(7.0, 5.0)); fig.subplots_adjust(hspace=0.45, wspace=0.3)
md = R["md_probes"]

def pooled(prefix):
    return np.mean([np.array(md[f"{prefix}_s{s}"]["hist"]) for s in (0, 100)], axis=0)

# (a) BAD of the production rows and probes
a = ax[0, 0]
for (p, lab), c in zip((("X300", "crystal 300 K"), ("X700", "crystal 700 K"),
                        ("M1500", "near-melt 1500 K"), ("A300", "amorphous 300 K")), C):
    a.plot(mid, pooled(p), color=c, lw=1.6, label=lab)
a.axvline(TET, color="0.6", lw=0.7, ls=":")
a.set_xlim(0, 180); a.set_xlabel("bond angle (°)"); a.set_ylabel("probability density (1/°)")
a.legend(frameon=False, loc="upper left"); a.set_title("Tersoff Si$_{0.5}$Ge$_{0.5}$ rows (MD snapshots)", fontsize=7.5)
a.text(-0.17, 1.05, "(a)", transform=a.transAxes, fontweight="bold")

# (b) one-number descriptor per frame
a = ax[0, 1]
groups = [("X300", "crystal\n\n300 K"), ("X700", "crystal\n\n700 K"), ("M1450", "near-\nmelt\n1450 K"),
          ("M1500", "near-\nmelt\n1500 K"), ("A300", "amorph.\n\n300 K"), ("A700", "amorph.\n\n700 K")]
rng = np.random.default_rng(0)
for k, (p, lab) in enumerate(groups):
    v = [f["std_deg"] for s in (0, 100) for f in md[f"{p}_s{s}"]["frames"]]
    c = C[0] if p[0] == "X" else (C[2] if p[0] == "M" else C[3])
    a.scatter(k + 0.12 * rng.standard_normal(len(v)), v, s=9, color=c, lw=0)
a.set_xticks(range(len(groups))); a.set_xticklabels([g[1] for g in groups], fontsize=5.8)
a.set_ylabel("spread of bond angles (°, s.d.)"); a.set_ylim(0, 19)
a.axhspan(7.5, 15.5, color="0.93", zorder=0); a.text(2.5, 11.5, "no frame falls in this band", ha="center", fontsize=6.5, color="0.35")
a.set_title("one number per snapshot (2 seeds × 11 frames)", fontsize=7.5)
a.text(-0.17, 1.05, "(b)", transform=a.transAxes, fontweight="bold")

# (c) MACE cells: angular distortion near carbon
a = ax[1, 0]; m = R["mace_cells"]
for (cell, key, lab), c in zip((("0.2_1_nC0_relaxed", "all", "Si$_{0.8}$Ge$_{0.2}$, no C"),
                                 ("0.2_1_nC4_relaxed", "C-centred", "at C"),
                                 ("0.2_1_nC4_relaxed", "Si-next-to-C-centred", "at Si bonded to C")), C):
    h = np.array(m[cell][key]["hist"])
    a.plot(mid, h, color=c, lw=1.6, label=f"{lab} (s.d. {m[cell][key]['std_deg']:.1f}°)")
a.axvline(TET, color="0.6", lw=0.7, ls=":")
a.set_xlim(85, 150); a.set_ylim(0, 0.62); a.set_xlabel("bond angle (°)"); a.set_ylabel("probability density (1/°)")
a.legend(frameon=False, loc="upper right"); a.set_title("MACE-MP-0 cells, Si$_{0.8}$Ge$_{0.2}$ + 4 C (1.9 at%)", fontsize=7.5)
a.text(-0.17, 1.05, "(c)", transform=a.transAxes, fontweight="bold")

# (d) radial profile around the embedded SiC particles
a = ax[1, 1]; pr = R["sic_radial"]["profile"]
r = np.array([0.5 * (p["r_lo_A"] + p["r_hi_A"]) for p in pr]) / 10
a.plot(r, [p["std_deg"] for p in pr], color=C[1], lw=1.6, marker="o", ms=3)
fc = np.array([p["frac_C"] for p in pr])
a.axvspan(0, r[fc > 0.3].max() + 0.05, color="0.92", zorder=0)
a.text(0.75, 30, "3C-SiC particle", fontsize=6.5, color="0.35", ha="center")
a.text(2.75, 30, "Si$_{0.7}$Ge$_{0.3}$ host", fontsize=6.5, color="0.35", ha="center")
a.set_xlim(0, 3.2); a.set_ylim(0, 35)
a.set_xlabel("distance from particle centre (nm)"); a.set_ylabel("spread of bond angles (°, s.d.)")
a.set_title("Tersoff box, two SiC particles of R = 2 nm (0 K)", fontsize=7.5)
a.text(-0.17, 1.05, "(d)", transform=a.transAxes, fontweight="bold")
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(HERE, f"fig_bond_angles.{ext}"), dpi=300, bbox_inches="tight")
