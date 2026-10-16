"""Fig. (fig:law): the fitted alloy law kappa(x, T) against its own
bulk-extrapolated Tersoff MD series and the other evidence sources, near
300 K (top) and 1100 K (bottom). Reads phase_c/final_law/final_law.json.
One column wide, panels stacked.

Spread: the band around the law is its leave-one-regime-out cross-validated
median error (stored in final_law.json). Tersoff series that were repeated
with independent seeds at the same (x, T) are drawn as the seed mean with a
bar spanning the seeds; all other series are single-seed.
"""
import json
from collections import defaultdict

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt

S.apply_style()

F = json.loads((S.PROJECT / "phase_c/final_law/final_law.json").read_text())
c = F["bulk_law_terms"]
cv = F["stageB_leave_one_regime_out_cv_medape_pct"] / 100.0


def law(x, T):
    return 1.0 / (c.get("1", 0) + c.get("x", 0) * x + c.get("x^2", 0) * x ** 2 + c.get("T", 0) * T)


OTHER = (("BTE-DFT", "bte_dft", "P", "DFT phonon BTE"),
         ("DB-CITRINE", "database", "D", "experimental database"),
         ("MACE-MD", "mace_md", "s", "MACE-MP MD (finite box)"))
TC = S.SOURCE_COLOURS["tersoff_md"]

fig, axes = plt.subplots(2, 1, figsize=(S.COL, 4.6), sharex=True, sharey=True)
for ax, (T, Tlo, Thi), tag in zip(axes, ((300, 250, 350), (1100, 950, 1250)), "ab"):
    xs = np.linspace(0.05, F["x_max"], 200)
    ax.fill_between(xs, law(xs, T) * (1 - cv), law(xs, T) * (1 + cv), color=S.GREY, alpha=0.55,
                    lw=0, label=f"cross-validated error ({100 * cv:.0f}%)")
    ax.plot(xs, law(xs, T), "-", color=S.SOURCE_COLOURS["law"], lw=1.4,
            label="fitted law (from Tersoff MD)")
    groups = defaultdict(list)
    for p in F["bulk_rows"]:
        if Tlo <= p["T"] <= Thi:
            groups[(p["x"], p["T"])].append(p["kappa"])
    single = [(x, ks[0]) for (x, _), ks in groups.items() if len(ks) == 1]
    ax.plot([s[0] for s in single], [s[1] for s in single], "o", color=TC, mfc="white", mew=1.1,
            ms=4.5, label="Tersoff MD, bulk limit (one seed)")
    rep = [(x, ks) for (x, _), ks in groups.items() if len(ks) > 1]
    for i, (x, ks) in enumerate(rep):
        m = float(np.mean(ks))
        ax.errorbar([x], [m], yerr=[[m - min(ks)], [max(ks) - m]], fmt="o", color=TC, mfc=TC,
                    mew=1.1, ms=4.5, capsize=2, lw=0.9,
                    label=f"Tersoff MD, bulk limit ({len(ks)} seeds, range)" if i == 0 else None)
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
axes[1].text(0.03, 0.04, "MACE-MP MD was run at 300 K only", transform=axes[1].transAxes,
             fontsize=7, color=S.INK, ha="left", va="bottom")
axes[1].set_xlabel(r"Ge fraction $x$ in Si$_{1-x}$Ge$_x$")
h, lab = axes[0].get_legend_handles_labels()
order = [1, 0, 2, 6, 3, 4, 5]
fig.legend([h[i] for i in order], [lab[i] for i in order], loc="outside lower center", ncol=1,
           handletextpad=0.4, borderaxespad=0.1)
S.save(fig, "fig_final_law")
