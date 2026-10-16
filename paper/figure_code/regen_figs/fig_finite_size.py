"""Fig. (fig:finitesize): finite-size extrapolation of the Tersoff MD series.

Seed-averaged 1/kappa against inverse box length 1/L (L from the simulation
box length along the heat flow, box_A[2]); error bars are the seed standard
deviation propagated to 1/kappa where a box size has more than one seed; lines
are least-squares fits in 1/L and stars the L -> infinity intercepts.
(a) the three alloy series; (b) the pure Si and Ge endpoints at 300 K, whose
intercepts fall below zero. Reads the committed rNEMD records
chpc/results/*.json (same selection as the earlier make_figures.py: the
standard protocol rows that carry no cross-section or swap override).
"""
import json
from collections import defaultdict

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

S.apply_style()

series = defaultdict(lambda: defaultdict(list))   # (x, T) -> ncz -> [(kappa, Lz_nm)]
for f in sorted((S.PROJECT / "chpc/results").glob("*.json")):
    d = json.loads(f.read_text())
    if "ncz" not in d or "kappa_W_mK" not in d:
        continue
    if d.get("cross_section") not in (None, "4x4") or d.get("swap_every") not in (None, 400):
        continue
    series[(d["x"], d["T"])][d["ncz"]].append((d["kappa_W_mK"], d["box_A"][2] / 10.0))

C = S.SOURCE_COLOURS["tersoff_md"]
PANELS = {
    "a": [((0.15, 300.0), "o", "-", C, r"$x$ = 0.15, 300 K"),
          ((0.5, 300.0), "s", "--", "#A06400", r"$x$ = 0.5, 300 K"),
          ((0.5, 1100.0), "^", ":", "#4A2E00", r"$x$ = 0.5, 1100 K")],
    "b": [((0.0, 300.0), "D", "-", C, "pure Si, 300 K"),
          ((1.0, 300.0), "v", "--", "#4A2E00", "pure Ge, 300 K")],
}

fig, axes = plt.subplots(2, 1, figsize=(S.COL, 4.6))
for ax, (tag, shown) in zip(axes, PANELS.items()):
    handles = []
    for key, mk, ls, col, lab in shown:
        by = series[key]
        if len(by) < 3:
            continue
        ncz = sorted(by)
        k = [np.array([v[0] for v in by[n]]) for n in ncz]
        L = np.array([np.mean([v[1] for v in by[n]]) for n in ncz])
        kmean = np.array([a.mean() for a in k])
        kerr = np.array([a.std(ddof=1) if len(a) > 1 else 0.0 for a in k])
        nseed = [len(a) for a in k]
        invL = 1.0 / L
        ax.errorbar(invL, 1.0 / kmean, yerr=kerr / kmean ** 2, color=col, marker=mk, ms=4,
                    ls="none", capsize=2, elinewidth=0.8)
        coef = np.polyfit(invL, 1.0 / kmean, 1)
        xs = np.linspace(0, invL.max() * 1.05, 20)
        ax.plot(xs, np.polyval(coef, xs), color=col, lw=0.9, ls=ls)
        ax.plot(0, coef[1], color=col, marker="*", ms=9, mec="white", mew=0.5, clip_on=False, zorder=5)
        kinf = 1 / coef[1] if coef[1] > 0 else float("nan")
        print(f"{lab}: seeds per box {nseed}, intercept 1/kappa = {coef[1]:.4f}, kappa_inf = {kinf:.2f}")
        handles.append(Line2D([], [], color=col, marker=mk, ms=4, ls=ls, lw=0.9, label=lab))
    handles.append(Line2D([], [], color=S.INK, marker="*", ms=8, ls="none", mec="white",
                          label=r"$L\to\infty$ intercept"))
    if tag == "b":
        ax.axhline(0, color=S.GREY, lw=0.7)
        ax.set_xticks([0, 0.01, 0.02, 0.03, 0.04])
    ax.set_xlim(left=-0.002)
    ax.set_ylabel(r"$1/\kappa$ (m K W$^{-1}$)")
    ax.set_title(f"({tag}) " + ("alloys" if tag == "a" else "pure endpoints"), loc="left")
    ax.legend(handles=handles, loc="upper left", title="Tersoff MD", title_fontsize=7,
              handlelength=2.4)
axes[1].set_xlabel(r"inverse box length $1/L$ (nm$^{-1}$)")
S.save(fig, "fig_finite_size")
