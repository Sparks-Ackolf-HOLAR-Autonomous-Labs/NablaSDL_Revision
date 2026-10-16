#!/usr/bin/env python3
"""Fig. bond angles, at print size (full width). Same data and panels as
bond_angles/make_bad_figure.py; reads bond_angles/bad_results.json.
(a) bond-angle distributions of Tersoff Si0.5Ge0.5 rows (mean of 2 seeds,
    band = range between the seeds); (b) angle spread per snapshot;
(c) MACE-MP-0 cells with 4 C; (d) radial spread around an SiC particle."""
import json

import numpy as np

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

R = json.load(open(S.PROJECT / "bond_angles" / "bad_results.json"))
TET = R["tetrahedral_deg"]
b = np.array(R["bins_deg"])
mid = 0.5 * (b[1:] + b[:-1])
md = R["md_probes"]
# colours for structural states (Paul Tol muted set), kept apart from the
# evidence-source colours used for sources in the other figures
C = {"crystal": "#332288", "crystal_hot": "#88CCEE", "melt": "#117733", "amorph": "#CC6677"}

fig, ax = plt.subplots(2, 2, figsize=(S.FULL, 4.6))


def seeds(prefix):
    return np.array([md[f"{prefix}_s{s}"]["hist"] for s in (0, 100)])


def tag(a, k):
    a.text(-0.13, 1.02, f"({k})", transform=a.transAxes, fontweight="bold", fontsize=9, va="bottom")


# (a)
a = ax[0, 0]
for p, lab, c in (("X300", "crystal, 300 K", C["crystal"]), ("X700", "crystal, 700 K", C["crystal_hot"]),
                  ("M1500", "near-melting, 1500 K", C["melt"]), ("A300", "amorphous, 300 K", C["amorph"])):
    h = seeds(p)
    a.fill_between(mid, h.min(0), h.max(0), color=c, alpha=0.25, lw=0)
    a.plot(mid, h.mean(0), color=c, lw=1.2, label=lab)
a.axvline(TET, color=S.GREY, lw=0.7, ls=":")
a.set_xlim(40, 180)
a.set_xlabel("bond angle (°)")
a.set_ylabel("probability density (1/°)")
a.legend(loc="upper right")
a.set_title(r"Tersoff MD, Si$_{0.5}$Ge$_{0.5}$")
tag(a, "a")

# (b)
a = ax[0, 1]
# categorical axis: one column per structural state and temperature
groups = [("X300", "crystal\n300 K"), ("X700", "crystal\n700 K"), ("M1450", "near-\nmelting\n1450 K"),
          ("M1500", "near-\nmelting\n1500 K"), ("A300", "amor-\nphous\n300 K"), ("A700", "amor-\nphous\n700 K")]
rng = np.random.default_rng(0)
for k, (p, lab) in enumerate(groups):
    v = [f["std_deg"] for s in (0, 100) for f in md[f"{p}_s{s}"]["frames"]]
    c = C["crystal"] if p[0] == "X" else (C["melt"] if p[0] == "M" else C["amorph"])
    a.scatter(k + 0.1 * rng.standard_normal(len(v)), v, s=7, color=c, lw=0, alpha=0.8)
    print(p, "snapshots:", len(v), "spread range", round(min(v), 2), round(max(v), 2))
a.set_xticks(range(len(groups)))
a.set_xticklabels([g[1] for g in groups], fontsize=7)
a.grid(axis="x", visible=False)
a.set_xlabel("structural state and temperature of the snapshot")
a.set_ylabel("bond-angle spread, s.d. (°)")
a.set_ylim(0, 19)
a.axhspan(7.5, 15.5, color=S.LIGHT, zorder=0)
a.set_title("one value per snapshot")
tag(a, "b")

# (c)
a = ax[1, 0]
m = R["mace_cells"]
for (cell, key, lab), c in zip((("0.2_1_nC0_relaxed", "all", "no C, all sites"),
                                ("0.2_1_nC4_relaxed", "C-centred", "at C"),
                                ("0.2_1_nC4_relaxed", "Si-next-to-C-centred", "at Si bonded to C")),
                               (C["crystal"], "#000000", C["amorph"])):
    h = np.array(m[cell][key]["hist"])
    a.plot(mid, h, color=c, lw=1.2, label=f"{lab} (s.d. {m[cell][key]['std_deg']:.1f}°)")
a.axvline(TET, color=S.GREY, lw=0.7, ls=":")
a.set_xlim(85, 150)
a.set_ylim(0, 0.62)
a.set_xlabel("bond angle (°)")
a.set_ylabel("probability density (1/°)")
a.legend(loc="upper right")
a.set_title(r"MACE-MP relaxed, Si$_{0.8}$Ge$_{0.2}$ + 4 C")
tag(a, "c")

# (d)
a = ax[1, 1]
pr = R["sic_radial"]["profile"]
r = np.array([0.5 * (p["r_lo_A"] + p["r_hi_A"]) for p in pr]) / 10
fc = np.array([p["frac_C"] for p in pr])
a.axvspan(0, r[fc > 0.3].max() + 0.05, color=S.LIGHT, zorder=0)
a.plot(r, [p["std_deg"] for p in pr], color=S.SOURCE_COLOURS["tersoff_md"], lw=1.2, marker="o", ms=3)
a.text(0.75, 31, "SiC particle", fontsize=7, color=S.INK, ha="center")
a.text(2.75, 31, r"Si$_{0.7}$Ge$_{0.3}$ host", fontsize=7, color=S.INK, ha="center")
a.set_xlim(0, 3.2)
a.set_ylim(0, 35)
a.set_xlabel("distance from particle centre (nm)")
a.set_ylabel("bond-angle spread, s.d. (°)")
a.set_title("Tersoff, SiC particle R = 2 nm, 0 K")
tag(a, "d")

S.save(fig, "fig_bond_angles")
