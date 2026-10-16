#!/usr/bin/env python3
"""Fig. SiGeC, at print size (full width). Reads
nano_sigec/results/sigec_results_m1c.json (substitutional carbon),
nano_sigec/m1c/m1c_summary.json (carbon energies) and, through
sigec_contrast.py, the measured radius-dependent SiC contrast of record
entry 110 (nano_sigec/small_sic/r50/r50_results.json) with its seed range.
(a) kappa_L vs carbon content; SiC lines at the measured contrast, bands =
    range over the two MD seeds behind the contrast;
(b) Ge fraction that matches the kappa_L of carbon-free Si0.8Ge0.2 (Ge-saving
    frontier), same bands;
(c) MACE-MP energies of where carbon goes (bars: range over configurations).
Colours: SiC radius on one sequential scale (dark = small), substitutional
carbon in greys; the evidence-source colours of the other figures are not
reused for these model curves."""
import json

import paper_fig_style as S
import sigec_contrast as SC

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

SG = S.PROJECT / "nano_sigec"
r = json.load(open(SG / "results" / "sigec_results_m1c.json"))
m1 = json.load(open(SG / "m1c" / "m1c_summary.json"))
KL = r"$\kappa_L$"
RAD_COL = {2.5: "#3B0F70", 5.0: "#8C2981", 10.0: "#DE4968", 100.0: "#F8A55F"}
WHICH = ("mid", "lo", "hi")

fig, ax = plt.subplots(1, 3, figsize=(S.FULL, 3.15))

sel = [q for q in r["D1"] if q["x"] == 0.2 and q["T"] == 300 and q["d_m"] == 0.3e-6]
k0 = sel[0]["kappa_noC"]


def curve(key):
    pts = sorted((q["y_C"], q["kappa"]) for q in sel if q["form"] == key)
    return [0] + [p[0] * 100 for p in pts], [k0] + [p[1] for p in pts]


for key, lab, c, ls in (("sub_eps0", "C on sites, mass only", "#8C8C8C", ":"),
                        ("sub_eps39", "C on sites, strain bound", S.INK, "-")):
    xs, ks = curve(key)
    ax[0].plot(xs, ks, ls, color=c, marker="o", ms=2.5, lw=1.1, label=lab)
ys = SC.YS
yc = [y for y in ys if y > 0]
for Rn, c in RAD_COL.items():
    k = {w: [SC.kappa(0.2, 300, y, Rn, w) for y in ys] for w in WHICH}
    lo, hi = SC.band([k[w] for w in WHICH])
    ax[0].fill_between([y * 100 for y in ys], lo, hi, color=c, alpha=0.25, lw=0)
    ax[0].plot([y * 100 for y in ys], k["mid"], "-", color=c, marker="o", ms=2.5, lw=1.1,
               label=f"SiC, R = {Rn:g} nm")
    xe = {w: [SC.x_equal(y, Rn, w) for y in yc] for w in WHICH}
    lo, hi = SC.band([xe[w] for w in WHICH])
    ax[1].fill_between([0] + [y * 100 for y in yc], [0.2] + list(lo), [0.2] + list(hi),
                       color=c, alpha=0.25, lw=0)
    ax[1].plot([0] + [y * 100 for y in yc], [0.2] + xe["mid"], "-", color=c, marker="o", ms=2.5, lw=1.1)
    i = ys.index(0.01)
    red = {w: 100 * (1 - k[w][i] / k0) for w in WHICH}
    sav = {w: 100 * (1 - xe[w][yc.index(0.01)] / 0.2) for w in WHICH}
    print(f"R={Rn:g} nm, 1 at% C: kappa_L lower by {red['mid']:.1f}% "
          f"(seeds {min(red.values()):.1f} to {max(red.values()):.1f}%); Ge saving {sav['mid']:.1f}% "
          f"(seeds {min(sav.values()):.1f} to {max(sav.values()):.1f}%)")
ax[0].set_xlabel("carbon content (at%)")
ax[0].set_ylabel(KL + r" (W m$^{-1}$ K$^{-1}$)")
ax[0].set_title(r"Si$_{0.8}$Ge$_{0.2}$, 300 K, 0.3 µm grains", fontsize=8)
ax[0].set_ylim(1.85, 3.05)

ax[1].axhline(0.2, color=S.GREY, lw=0.7, ls="--")
ax[1].set_xlabel("carbon content (at%)")
ax[1].set_ylabel("Ge fraction $x$")
ax[1].set_title(r"Ge at the $\kappa_L$ of Si$_{0.8}$Ge$_{0.2}$, 300 K", fontsize=8)

xs = [0.0, 0.2, 0.5]
pe = [m1["per_x"][f"{x:g}"]["dE_prec_eV"] for x in xs]
pm = [m1["per_x"][f"{x:g}"]["dE_prec_mean_eV"] for x in xs]
ax[2].errorbar(xs, pm, yerr=[[m - min(v) for m, v in zip(pm, pe)], [max(v) - m for m, v in zip(pm, pe)]],
               fmt="o-", color=S.INK, ms=3, lw=1.1, capsize=2, label="C leaves lattice,\nforms SiC")
se = [[s["dE_site"] for s in m1["per_x"][f"{x:g}"]["site_pref"]] for x in xs[1:]]
sm = [m1["per_x"][f"{x:g}"]["dE_site_mean_eV"] for x in xs[1:]]
ax[2].errorbar(xs[1:], sm, yerr=[[m - min(v) for m, v in zip(sm, se)], [max(v) - m for m, v in zip(sm, se)]],
               fmt="s--", color=S.GREY, ms=3, lw=1.1, capsize=2, label="C beside Ge,\nnot Si")
ax[2].axhline(0, color=S.GREY, lw=0.7)
ax[2].set_xlabel("host Ge fraction $x$")
ax[2].set_ylabel("energy per C (eV)")
ax[2].set_title("Where carbon goes (MACE-MP)", fontsize=8)
ax[2].legend(loc="center right")
for k, a in zip("abc", ax):
    a.text(-0.2, 1.1, f"({k})", transform=a.transAxes, fontweight="bold", fontsize=9, va="bottom")
h, lab = ax[0].get_legend_handles_labels()
h.append(Patch(fc=S.GREY, alpha=0.35, lw=0))
lab.append("seed range of the SiC contrast")
fig.legend(h, lab, loc="outside lower center", ncol=4, handlelength=1.6, columnspacing=1.0,
           handletextpad=0.4)
S.save(fig, "fig_sigec")
