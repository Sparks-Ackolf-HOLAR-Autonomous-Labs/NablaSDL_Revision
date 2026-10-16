#!/usr/bin/env python3
"""Paper 1 figure: the final kappa(x, T) law (Tersoff-1989 CHPC-MD party,
bulk-extrapolated) against its own bulk series and the other parties.
Reads final_law.json. Usage: python3 make_final_law_figure.py <out.pdf>"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, "final_law.json")))
c = F["bulk_law_terms"]


def law(x, T):
    return 1.0 / (c.get("1", 0) + c.get("x", 0) * x + c.get("x^2", 0) * x ** 2 + c.get("T", 0) * T)


fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
for ax, (T, Tlo, Thi) in zip(axes, ((300, 250, 350), (1100, 950, 1250))):
    xs = np.linspace(0.05, F["x_max"], 200)
    ax.plot(xs, law(xs, T), "-", color="#1f77b4", lw=2, label="law (Tersoff-MD, bulk)")
    bs = [p for p in F["bulk_rows"] if Tlo <= p["T"] <= Thi]
    ax.plot([p["x"] for p in bs], [p["kappa"] for p in bs], "o", color="#1f77b4",
            mfc="none", ms=5, label="CHPC-MD series, 1/L extrapolated")
    for name, mk, col in (("BTE-DFT", "^", "k"), ("DB-CITRINE", "D", "#2ca02c"),
                          ("MACE-MD", "s", "#d62728")):
        ps = [p for p in F["comparison"][name]["points"] if Tlo <= p["T"] <= Thi]
        if ps:
            lab = name + (" (finite box)" if name == "MACE-MD" else "")
            ax.plot([p["x"] for p in ps], [p["kappa"] for p in ps], mk, color=col, label=lab)
    ax.axvspan(F["x_max"], 1.0, color="0.9")
    ax.text(0.925, 0.6, "scope-limited\n(dilute Ge)", fontsize=7, ha="center", rotation=90)
    ax.set_yscale("log")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Ge fraction x")
    ax.set_title(f"T near {T} K")
axes[0].set_ylabel(r"$\kappa$ (W m$^{-1}$ K$^{-1}$)")
h, l = axes[0].get_legend_handles_labels()
axes[1].legend(h, l, fontsize=7, loc="lower center")
fig.tight_layout()
fig.savefig(sys.argv[1])
fig.savefig(sys.argv[1].rsplit(".", 1)[0] + ".png", dpi=200)
