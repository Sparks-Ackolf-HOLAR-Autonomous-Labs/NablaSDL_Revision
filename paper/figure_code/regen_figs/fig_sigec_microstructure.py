"""Main-text Fig. (fig:microstructure): the target SiGeC material.

(a) schematic of the target microstructure (sintered SiGe grains with
few-nanometre SiC precipitates, coarse admixed SiC powder for comparison) with
an atomic zoom of substitutional carbon leaving its site; the 1.44 to 1.68 eV
range is the converged MACE-MP-0 precipitation energy of
nano_sigec/m1c/m1c_summary.json. (b) change in kappa_L per 1 at% C against
SiC radius for Si0.8Ge0.2 at 300 K and three effective grain sizes, at the
measured radius-dependent contrast (sigec_contrast.py; solid up to the largest
measured radius, 5 nm, dashed beyond), band = range over the two MD seeds;
the shaded interval is the particle size reported by Zhao et al.
Full journal width. Drawn in the style of the earlier ESI panel
(fig_sigec_layers.py), which now holds only the length-scale map.
"""
import json

import numpy as np
import paper_fig_style as S
import sigec_contrast as SC
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, ConnectionPatch, Polygon, Rectangle
from scipy.spatial import Voronoi

S.apply_style()
m1 = json.loads((S.PROJECT / "nano_sigec/m1c/m1c_summary.json").read_text())
dE = [v for x in ("0", "0.2", "0.5") for v in m1["per_x"][x]["dE_prec_eV"]]
dmean = [m1["per_x"][x]["dE_prec_mean_eV"] for x in ("0", "0.2", "0.5")]
print("precipitation energy per C, means by host x:", [round(v, 3) for v in dmean])

W, H = S.FULL, 2.95
fig = plt.figure(figsize=(W, H), layout="none")


def axes_in(x, y, w, h):
    """Axes placed in inches from the lower-left corner."""
    return fig.add_axes([x / W, y / H, w / W, h / H])


PREC, POWDER, GRAIN, EDGE = S.INK, "white", "#EFEFEF", "#9A9A9A"

# ---------------------------------------------------------- (a) microstructure
fig.text(0.05 / W, 2.90 / H, "(a) Target microstructure (schematic)", fontsize=9, va="top", color=S.INK)
ax = axes_in(0.10, 0.62, 1.95, 1.95)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect("equal")
ax.axis("off")
rng = np.random.default_rng(7)
vor = Voronoi(rng.uniform(-0.2, 1.2, size=(60, 2)))
for reg in vor.point_region:
    verts = vor.regions[reg]
    if -1 in verts or not verts:
        continue
    ax.add_patch(Polygon(vor.vertices[verts], closed=True, fc=GRAIN, ec=EDGE, lw=0.8, zorder=1))
for cx, cy in [(0.22, 0.30), (0.74, 0.70)]:
    ax.add_patch(Circle((cx, cy), 0.05, fc=POWDER, ec=S.INK, lw=0.8, hatch="////", zorder=3))
for cx, cy in rng.uniform(0.04, 0.96, size=(140, 2)):
    ax.add_patch(Circle((cx, cy), 0.007, fc=PREC, ec="none", zorder=3))
ax.add_patch(Rectangle((0, 0), 1, 1, fc="none", ec=S.INK, lw=0.8, zorder=4))
zx, zy = 0.52, 0.38
ax.add_patch(Rectangle((zx, zy), 0.07, 0.07, fc="none", ec=S.INK, lw=1.0, zorder=5))

ins = axes_in(2.30, 0.92, 1.35, 1.35)
ins.set_xlim(-0.5, 6.5)
ins.set_ylim(-0.5, 6.5)
ins.set_aspect("equal")
ins.set_xticks([])
ins.set_yticks([])
ins.grid(False)
for s in ins.spines.values():
    s.set_visible(True)
    s.set_color(S.INK)
lat = [(i, j) for i in range(7) for j in range(7)]
ge = set(map(tuple, rng.choice(lat, 10, replace=False)))
for (i, j) in lat:
    if (i, j) in {(1, 5), (5, 1)}:
        ins.add_patch(Circle((i, j), 0.26, fc="white", ec=S.INK, lw=0.8))      # B or P dopant
    elif (i, j) == (4, 4):
        ins.add_patch(Circle((i, j), 0.20, fc="black", ec="none"))           # substitutional C
    elif (i, j) in ge:
        ins.add_patch(Circle((i, j), 0.36, fc="#6E6E6E", ec="none"))         # Ge
    else:
        ins.add_patch(Circle((i, j), 0.30, fc="#C8C8C8", ec="none"))         # Si
ins.add_patch(Circle((1.5, 1.8), 0.95, fc=PREC, ec="none", zorder=3))
ins.text(1.5, 1.8, "SiC", ha="center", va="center", fontsize=7, color="white", zorder=4)
ins.annotate("", xy=(2.1, 2.5), xytext=(3.8, 3.8), arrowprops=dict(arrowstyle="->", color=S.INK, lw=0.9))
ins.set_title(f"C leaves its site for SiC\n({-max(dmean):.2f} to {-min(dmean):.2f} eV per C)",
              fontsize=7, color=S.INK, pad=3)
for (xa, ya), (xb, yb) in [((zx + 0.07, zy + 0.07), (-0.5, 6.5)), ((zx + 0.07, zy), (-0.5, -0.5))]:
    fig.add_artist(ConnectionPatch((xa, ya), (xb, yb), coordsA=ax.transData, coordsB=ins.transData,
                                   color=S.GREY, lw=0.6))
handles = [
    (Rectangle((0, 0), 1, 1, fc=GRAIN, ec=EDGE), "SiGe grain"),
    (Circle((0, 0), 1, fc=PREC), "few-nm SiC (target)"),
    (Rectangle((0, 0), 1, 1, fc=POWDER, ec=S.INK, hatch="////"), "SiC powder (≥ 100 nm)"),
    (Circle((0, 0), 1, fc="#C8C8C8"), "Si"),
    (Circle((0, 0), 1, fc="#6E6E6E"), "Ge"),
    (Circle((0, 0), 1, fc="black"), "substitutional C"),
    (Circle((0, 0), 1, fc="white", ec=S.INK), "B or P dopant"),
]
fig.legend([h for h, _ in handles], [lab for _, lab in handles], loc="lower left",
           bbox_to_anchor=(0.05 / W, 0.0), ncol=3, handlelength=1.0, handletextpad=0.4,
           columnspacing=0.8, borderaxespad=0.1)

# ------------------------------------------------------------ (b) data panel
fig.text(3.95 / W, 2.90 / H, "(b) Carbon effect against SiC radius", fontsize=9, va="top", color=S.INK)
ax = axes_in(4.45, 0.42, 2.22, 2.17)
R = np.geomspace(2.5, 150, 19)
GRAINS = [(1e-7, "0.1 μm", "#B5B5B5"), (3e-7, "0.3 μm", "#6F6F6F"), (5e-7, "0.5 μm", "#1F1F1F")]
for dm, lab, col in GRAINS:
    k0 = SC.kappa(0.2, 300, 0.0, 1.0, d=dm)
    ch = {w: np.array([100 * (SC.kappa(0.2, 300, 0.01, Rn, w, d=dm) / k0 - 1) for Rn in R])
          for w in ("mid", "lo", "hi")}
    lo, hi = SC.band([ch["mid"], ch["lo"], ch["hi"]])
    ax.fill_between(R, lo, hi, color=col, alpha=0.3, lw=0)
    inside = R <= 5.0 + 1e-9
    ax.plot(R[inside], ch["mid"][inside], color=col, lw=1.3, label=lab)
    ax.plot(R[~inside | (np.arange(len(R)) == inside.sum() - 1)],
            ch["mid"][~inside | (np.arange(len(R)) == inside.sum() - 1)], color=col, lw=1.1, ls="--")
    print(f"grain {lab}: change per 1 at% C at R = 2.5 nm {ch['mid'][0]:.1f}% "
          f"(seeds {min(ch['lo'][0], ch['hi'][0]):.1f} to {max(ch['lo'][0], ch['hi'][0]):.1f}%), "
          f"at R = 100 nm {np.interp(100, R, ch['mid']):.2f}%")
ax.axvspan(100, 300, color=S.LIGHT, lw=0, zorder=0)
ax.text(170, -4.2, "Zhao et al.\nSiC size", ha="center", va="center", fontsize=7, color=S.INK)
ax.axhline(0, color=S.GREY, lw=0.6)
ax.set_xscale("log")
ax.set_xlim(2.2, 300)
ax.set_xticks([2.5, 5, 10, 25, 50, 100])
ax.set_xticklabels(["2.5", "5", "10", "25", "50", "100"])
ax.minorticks_off()
ax.set_xlabel("SiC particle radius R (nm)")
ax.set_ylabel(r"change in $\kappa_L$ per 1 at% C (%)")
ax.legend(loc="lower right", bbox_to_anchor=(0.80, 0.0), title="grain size", title_fontsize=7,
          handlelength=1.4)

S.save(fig, "fig_sigec_microstructure")
