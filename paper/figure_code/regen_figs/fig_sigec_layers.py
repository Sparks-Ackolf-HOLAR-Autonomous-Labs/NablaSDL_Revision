"""ESI Fig. (fig:layers): scattering layers of nanostructured SiGeC by length scale.

One panel: each scattering layer drawn at its length scale with a short label
of its effect on kappa_L. Values: alloy baseline from the DFT phonon BTE source;
carbon energies and dopant bound from nano_sigec RESULTS.md (main text); SiC
precipitate range 2.2 to 6.3% per at% C at the measured radius-dependent
contrast (R = 10 to 2.5 nm, Si0.8Ge0.2, 300 K, 0.3 um grains; printed by
fig_sigec.py); coarse particles below 2% under both contrast limits (main
text). The microstructure schematic and the radius dependence formerly in
this figure are drawn in the main text by fig_sigec_microstructure.py.
Full journal width. Pure layout, no data file read.
"""
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

S.apply_style()

W, H = S.FULL, 2.45
fig = plt.figure(figsize=(W, H), layout="none")
ax = fig.add_axes([1.75 / W, 0.42 / H, 4.90 / W, 1.85 / H])
ax.set_xscale("log")
ax.set_xlim(0.05, 1e5)
ax.set_ylim(0.45, 6.0)
ax.grid(axis="y", visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
rows = [  # y, lo, hi, layer, effect
    (5.0, 0.2, 0.6, "Si/Ge mass disorder", r"$\kappa$ at $x$ = 0.5 about 1/25 of pure Si"),
    (4.0, 0.2, 0.6, "substitutional C, B, P", "C leaves its site; B, P: at most 0.43%"),
    (3.0, 2.5, 10, "SiC, R 2.5 to 10 nm", "2.2 to 6.3% lower per at% C"),
    (2.0, 100, 300, "SiC, R ≥ 100 nm", "below 2% per at% C"),
    (1.0, 100, 900, "grains, 0.1 to 0.9 μm", "sintered SiGe"),
]
for y, lo, hi, name, what in rows:
    ax.add_patch(Rectangle((lo, y - 0.3), hi - lo, 0.6, fc=S.INK if "2.5 to 10" in name else S.GREY,
                           ec="none", zorder=3))
    ax.text(hi * 1.3, y, what, ha="left", va="center", fontsize=7, color=S.INK)
ax.set_yticks([r[0] for r in rows])
ax.set_yticklabels([r[3] for r in rows], fontsize=7)
ax.set_xticks([0.1, 1, 10, 100, 1e3, 1e4])
ax.set_xticklabels(["0.1", "1", "10", "100", "1000", "10000"])
ax.set_xlabel("length scale (nm)")
ax.annotate("", xy=(3e3, 5.72), xytext=(8, 5.72), arrowprops=dict(arrowstyle="<->", color=S.INK, lw=0.8))
ax.text(155, 5.60, "heat-carrying phonon wavelengths", ha="center", va="top", fontsize=7,
        style="italic", color=S.INK)
S.save(fig, "fig_sigec_layers")
