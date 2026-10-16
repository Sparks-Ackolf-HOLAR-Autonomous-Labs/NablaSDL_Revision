"""Fig. (fig:law): the fitted alloy law kappa(x, T) against its own
bulk-extrapolated Tersoff MD series and the other evidence sources, near
300 K (top) and 1100 K (bottom). Reads phase_c/final_law/final_law.json.
One column wide, panels stacked.
"""
import json

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt

S.apply_style()

F = json.loads((S.PROJECT / "phase_c/final_law/final_law.json").read_text())
c = F["bulk_law_terms"]


def law(x, T):
    return 1.0 / (c.get("1", 0) + c.get("x", 0) * x + c.get("x^2", 0) * x ** 2 + c.get("T", 0) * T)


OTHER = (("BTE-DFT", "bte_dft", "P", "DFT phonon BTE"),
         ("DB-CITRINE", "database", "D", "experimental database"),
         ("MACE-MD", "mace_md", "s", "MACE-MP MD (finite box)"))

fig, axes = plt.subplots(2, 1, figsize=(S.COL, 4.3), sharex=True, sharey=True)
for ax, (T, Tlo, Thi), tag in zip(axes, ((300, 250, 350), (1100, 950, 1250)), "ab"):
    xs = np.linspace(0.05, F["x_max"], 200)
    ax.plot(xs, law(xs, T), "-", color=S.SOURCE_COLOURS["law"], lw=1.4,
            label="fitted law (from Tersoff MD)")
    bs = [p for p in F["bulk_rows"] if Tlo <= p["T"] <= Thi]
    ax.plot([p["x"] for p in bs], [p["kappa"] for p in bs], "o", color=S.SOURCE_COLOURS["tersoff_md"],
            mfc="white", mew=1.1, ms=4.5, label="Tersoff MD, extrapolated to bulk")
    for name, key, mk, lab in OTHER:
        ps = [p for p in F["comparison"][name]["points"] if Tlo <= p["T"] <= Thi]
        ax.plot([p["x"] for p in ps], [p["kappa"] for p in ps], mk, color=S.SOURCE_COLOURS[key],
                ms=4.5, mec="white", mew=0.4, label=lab)
    ax.axvspan(F["x_max"], 1.0, color=S.LIGHT, lw=0)
    ax.text((F["x_max"] + 1.0) / 2, 0.5, "outside scope", transform=ax.get_xaxis_transform(),
            ha="center", va="center", rotation=90, fontsize=7, color=S.INK)
    ax.set_yscale("log")
    ax.set_xlim(0, 1)
    ax.set_ylabel(r"$\kappa$ (W m$^{-1}$ K$^{-1}$)")
    ax.set_title(f"({tag}) near {T} K", loc="left")
axes[1].set_xlabel(r"Ge fraction $x$ in Si$_{1-x}$Ge$_x$")
h, lab = axes[0].get_legend_handles_labels()
fig.legend(h, lab, loc="outside lower center", ncol=2, handletextpad=0.3, columnspacing=0.8)
S.save(fig, "fig_final_law")
