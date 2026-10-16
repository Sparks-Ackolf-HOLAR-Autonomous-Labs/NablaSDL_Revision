#!/usr/bin/env python3
"""Fig. SiGeC, at print size (full width). Same data and panels as
../make_sigec_figure.py; reads nano_sigec/results/sigec_results_m1c.json and
nano_sigec/m1c/m1c_summary.json.
(a) kappa_L vs carbon content; SiC lines use the measured radius-dependent
    contrast adopted at ledger entry 110 (nano_sigec/small_sic/r50/measured_curves.json);
(b) Ge fraction that matches the kappa_L of carbon-free Si0.8Ge0.2 (Ge-saving frontier);
(c) MACE-MP energies of where carbon goes (bars: range over configurations)."""
import json

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

SG = S.PROJECT / "nano_sigec"
r = json.load(open(SG / "results" / "sigec_results_m1c.json"))
m1 = json.load(open(SG / "m1c" / "m1c_summary.json"))
mc = json.load(open(SG / "small_sic" / "r50" / "measured_curves.json"))
KL = r"$\kappa_L$"

fig, ax = plt.subplots(1, 3, figsize=(S.FULL, 2.8))

sel = [q for q in r["D1"] if q["x"] == 0.2 and q["T"] == 300 and q["d_m"] == 0.3e-6]
k0 = sel[0]["kappa_noC"]


def curve(key):
    pts = sorted((q["y_C"], q["kappa"]) for q in sel if q["form"] == key)
    return [0] + [p[0] * 100 for p in pts], [k0] + [p[1] for p in pts]


styles = [("sub_eps0", "C on sites, mass only", "#56B4E9", ":"),
          ("sub_eps39", "C on sites, strain bound", "#0072B2", "-"),
          ("SiC_R2.5nm", "SiC, R = 2.5 nm", "#D55E00", "-"),
          ("SiC_R5nm", "SiC, R = 5 nm", "#009E73", "-"),
          ("SiC_R10nm", "SiC, R = 10 nm", "#E69F00", "-"),
          ("SiC_R100nm", "SiC, R = 100 nm", "#8C8C8C", "-")]
for key, lab, c, ls in styles:
    if key.startswith("SiC"):
        rk = "R" + key.split("_R")[1].replace("nm", "")
        pts = mc["panel_a_x0.2"][rk]
        xs, ks = [p[0] * 100 for p in pts], [p[1] for p in pts]
    else:
        xs, ks = curve(key)
    ax[0].plot(xs, ks, ls, color=c, marker="o", ms=2.5, lw=1.1, label=lab)
ax[0].set_xlabel("carbon content (at%)")
ax[0].set_ylabel(KL + r" (W m$^{-1}$ K$^{-1}$)")
ax[0].set_title(r"Si$_{0.8}$Ge$_{0.2}$, 300 K, 0.3 µm grains", fontsize=8)
ax[0].set_ylim(1.85, 3.05)
ax[0].legend(loc="lower left", handlelength=1.5, labelspacing=0.25, borderaxespad=0.2)

ax[1].axhline(0.2, color=S.GREY, lw=0.7, ls="--")
for key, lab, c, ls in styles[2:]:
    rk = "R" + key.split("_R")[1].replace("nm", "")
    row = [p for p in mc["panel_b_x_equal_kappa"][rk] if p[1] is not None]
    ax[1].plot([0] + [p[0] * 100 for p in row], [0.2] + [p[1] for p in row], ls, color=c,
               marker="o", ms=2.5, lw=1.1, label=lab)
ax[1].set_xlabel("carbon content (at%)")
ax[1].set_ylabel("Ge fraction $x$")
ax[1].set_title(r"Ge at the $\kappa_L$ of Si$_{0.8}$Ge$_{0.2}$, 300 K", fontsize=8)

xs = [0.0, 0.2, 0.5]
pe = [m1["per_x"][f"{x:g}"]["dE_prec_eV"] for x in xs]
pm = [m1["per_x"][f"{x:g}"]["dE_prec_mean_eV"] for x in xs]
ax[2].errorbar(xs, pm, yerr=[[m - min(v) for m, v in zip(pm, pe)], [max(v) - m for m, v in zip(pm, pe)]],
               fmt="o-", color="#D55E00", ms=3, lw=1.1, capsize=2, label="C leaves lattice, forms SiC")
se = [[s["dE_site"] for s in m1["per_x"][f"{x:g}"]["site_pref"]] for x in xs[1:]]
sm = [m1["per_x"][f"{x:g}"]["dE_site_mean_eV"] for x in xs[1:]]
ax[2].errorbar(xs[1:], sm, yerr=[[m - min(v) for m, v in zip(sm, se)], [max(v) - m for m, v in zip(sm, se)]],
               fmt="s--", color="#0072B2", ms=3, lw=1.1, capsize=2, label="C beside Ge, not Si")
ax[2].axhline(0, color=S.GREY, lw=0.7)
ax[2].set_xlabel("host Ge fraction $x$")
ax[2].set_ylabel("energy per C (eV)")
ax[2].set_title("Where carbon goes (MACE-MP)", fontsize=8)
ax[2].legend(loc="center right")
for k, a in zip("abc", ax):
    a.text(-0.2, 1.1, f"({k})", transform=a.transAxes, fontweight="bold", fontsize=9, va="bottom")
S.save(fig, "fig_sigec")
