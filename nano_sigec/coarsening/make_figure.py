#!/usr/bin/env python3
"""Figure: mean SiC radius vs hold time, bands over literature parameters, r0 = 1-2 nm and PSD width.
Single-column print size (3.3 in wide), 8 pt fonts. Output: fig_coarsening.png / .pdf"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
res = json.loads((HERE / "results" / "coarsening_results.json").read_text())
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
                     "legend.fontsize": 8, "font.family": "DejaVu Sans", "axes.linewidth": 0.6})
T_SHOW = [1073, 1173, 1273, 1373, 1473, 1573]
cmap = plt.get_cmap("viridis")
colors = {T: cmap(0.9 - 0.85 * i / (len(T_SHOW) - 1)) for i, T in enumerate(T_SHOW)}
tg = np.logspace(-3, 6, 400)   # hours

fig, ax = plt.subplots(figsize=(3.3, 2.75), dpi=300)
ax.axvspan(5 / 60, 0.5, color="0.88", lw=0)
ax.axvspan(1, 4, color="0.80", lw=0)
ax.axvline(1e4, color="0.5", lw=0.6, ls=":")
for T in T_SHOW:
    rows = [r for r in res["class_model"][str(T)] if r["sigma"].startswith("pizzagalli")]
    curves = []
    for r in rows:
        tr = np.array(r["traj_h_nm"])
        # light smoothing in log r (5-point running mean) removes the steps caused by
        # discrete size classes vanishing one at a time
        lr = np.log(tr[:, 1]); k = 5
        lr_s = np.convolve(np.pad(lr, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        curves.append(np.exp(np.interp(np.log10(tg), np.log10(tr[:, 0]), lr_s, left=np.nan, right=np.nan)))
    curves = np.array(curves)
    lo, hi = np.nanmin(curves, axis=0), np.nanmax(curves, axis=0)
    ax.fill_between(tg, lo, hi, color=colors[T], alpha=0.55, lw=0)
    with np.errstate(all="ignore"):
        mid = np.sqrt(lo * hi)
    ax.plot(tg, mid, color=colors[T], lw=0.9)
    # direct labels, staggered in height, else at the right edge
    ylab = {1573: 15, 1473: 30, 1373: 15, 1273: 30}.get(T, 25)
    j = np.where(mid >= ylab)[0]
    if j.size:
        ax.text(tg[j[0]] / 1.5, ylab, f"{T} K", fontsize=8, color=colors[T], ha="right", va="center")
    else:
        ax.text(9e5, mid[-1] * 1.12, f"{T} K", fontsize=8, color=colors[T], ha="right", va="bottom")
for y in (2.5, 5, 10):
    ax.axhline(y, color="k", lw=0.4, ls="--")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1e-3, 1e6); ax.set_ylim(0.8, 40)
ax.set_yticks([1, 2.5, 5, 10, 20, 40]); ax.set_yticklabels(["1", "2.5", "5", "10", "20", "40"])
ax.set_xlabel("Hold time (h)")
ax.set_ylabel("Mean SiC radius (nm)")
ax.text(0.2, 0.86, "SPS", ha="center", fontsize=8)
ax.text(2.0, 0.86, "HP", ha="center", fontsize=8)
ax.text(1e4 * 1.3, 0.86, "$10^4$ h", fontsize=8, color="0.35")
fig.tight_layout(pad=0.3)
fig.savefig(HERE / "fig_coarsening.png", dpi=300)
fig.savefig(HERE / "fig_coarsening.pdf")
print("written", HERE / "fig_coarsening.png")
