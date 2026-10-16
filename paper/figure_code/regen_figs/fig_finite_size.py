"""Fig. (fig:finitesize): finite-size extrapolation of the Tersoff MD series.

Seed-averaged 1/kappa against inverse box length 1/L (L from the simulation
box length along the heat flow, box_A[2]); error bars are the seed standard
deviation propagated to 1/kappa; lines are least-squares fits in 1/L and stars
the L -> infinity intercepts. Reads the committed rNEMD records
chpc/results/*.json (same selection as the earlier make_figures.py).
"""
import json
from collections import defaultdict

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt

S.apply_style()

series = defaultdict(lambda: defaultdict(list))   # (x, T) -> ncz -> [(kappa, Lz_nm)]
for f in sorted((S.PROJECT / "chpc/results").glob("*.json")):
    d = json.loads(f.read_text())
    if "ncz" not in d or "kappa_W_mK" not in d:
        continue
    if d.get("cross_section") not in (None, "4x4") or d.get("swap_every") not in (None, 400):
        continue
    series[(d["x"], d["T"])][d["ncz"]].append((d["kappa_W_mK"], d["box_A"][2] / 10.0))

SHOWN = [((0.15, 300.0), "o", "-"), ((0.5, 300.0), "s", "--"), ((0.5, 1100.0), "^", ":")]
C = S.SOURCE_COLOURS["tersoff_md"]
SHADES = {(0.15, 300.0): C, (0.5, 300.0): "#A06400", (0.5, 1100.0): "#4A2E00"}

fig, ax = plt.subplots(figsize=(S.COL, 2.6))
for key, mk, ls in SHOWN:
    by = series[key]
    if len(by) < 3:
        continue
    ncz = sorted(by)
    k = [np.array([v[0] for v in by[n]]) for n in ncz]
    L = np.array([np.mean([v[1] for v in by[n]]) for n in ncz])
    kmean = np.array([a.mean() for a in k])
    kerr = np.array([a.std() if len(a) > 1 else 0.0 for a in k])
    invL = 1.0 / L
    col = SHADES[key]
    x, T = key
    ax.errorbar(invL, 1.0 / kmean, yerr=kerr / kmean ** 2, color=col, marker=mk, ms=4,
                ls="none", capsize=2, elinewidth=0.8, label=rf"$x$ = {x:g}, {T:g} K")
    coef = np.polyfit(invL, 1.0 / kmean, 1)
    xs = np.linspace(0, invL.max() * 1.05, 20)
    ax.plot(xs, np.polyval(coef, xs), color=col, lw=0.9, ls=ls)
    ax.plot(0, coef[1], color=col, marker="*", ms=9, mec="white", mew=0.5, clip_on=False, zorder=5)
ax.set_xlim(left=-0.002)
ax.set_xlabel(r"inverse box length $1/L$ (nm$^{-1}$)")
ax.set_ylabel(r"$1/\kappa$ (m K W$^{-1}$)")
ax.legend(loc="upper left", title="Tersoff MD", title_fontsize=7)
S.save(fig, "fig_finite_size")
