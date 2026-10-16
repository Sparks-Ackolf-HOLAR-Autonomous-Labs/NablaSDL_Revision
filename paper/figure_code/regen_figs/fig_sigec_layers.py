"""ESI Fig. (fig:layers): structure of nanostructured SiGeC.

(a) scattering layers by length scale and what each does to kappa_L (labels
quote the values of the earlier make_sigec_story_figs.py, from nano_sigec
RESULTS.md); (b) schematic of the target microstructure with an atomic
zoom; (c) change in kappa_L per 1 at% C against SiC radius for Si0.8Ge0.2 at
300 K and three effective grain sizes, band = SiC contrast bracket (solid:
stiffness bound, dashed: density bound). Panel (c) reads
nano_sigec/results/sigec_results_m1c.json. Full journal width.
"""
import json

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, ConnectionPatch, Polygon, Rectangle
from scipy.spatial import Voronoi

S.apply_style()
d = json.loads((S.PROJECT / "nano_sigec/results/sigec_results_m1c.json").read_text())

W, H = S.FULL, 5.55
fig = plt.figure(figsize=(W, H), layout="none")


def axes_in(x, y, w, h):
    """Axes placed in inches from the lower-left corner."""
    return fig.add_axes([x / W, y / H, w / W, h / H])


PREC, POWDER, GRAIN, EDGE = S.INK, "white", "#EFEFEF", "#9A9A9A"

# ---------------------------------------------------------------- (a) ladder
ax = axes_in(1.95, 3.32, 4.70, 1.95)
ax.set_xscale("log")
ax.set_xlim(0.05, 1e5)
ax.set_ylim(0.45, 6.0)
ax.grid(axis="y", visible=False)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
rows = [  # y, lo, hi, layer, effect, text side
    (5.0, 0.2, 0.6, "Si/Ge mass disorder",
     r"alloy baseline: $\kappa$ at $x$ = 0.5 is about 1/25 of pure Si (DFT phonon BTE)", "right"),
    (4.0, 0.2, 0.6, "substitutional C, B, P",
     "C is unstable on a site (1.44 to 1.68 eV gained as SiC); B, P: at most 0.43%", "right"),
    (3.0, 2.5, 10, "SiC precipitates, R 2.5 to 10 nm",
     r"main carbon effect: 11 to 27% lower $\kappa_L$ per at% C", "right"),
    (2.0, 100, 300, "SiC particles, R ≥ 100 nm",
     "about 1% per at% C (SiC powder)", "right"),
    (1.0, 100, 900, "grains, effective 0.1 to 0.9 μm",
     "how sintered SiGe behaves", "right"),
]
for y, lo, hi, name, what, side in rows:
    ax.add_patch(Rectangle((lo, y - 0.3), hi - lo, 0.6, fc=PREC if "precipitates" in name else S.GREY,
                           ec="none", zorder=3))
    if side == "right":
        ax.text(hi * 1.25, y, what, ha="left", va="center", fontsize=7, color=S.INK)
    else:
        ax.text(lo / 1.25, y, what, ha="right", va="center", fontsize=7, color=S.INK)
ax.set_yticks([r[0] for r in rows])
ax.set_yticklabels([r[3] for r in rows], fontsize=7)
ax.set_xticks([0.1, 1, 10, 100, 1e3, 1e4])
ax.set_xticklabels(["0.1", "1", "10", "100", "1000", "10000"])
ax.set_xlabel("length scale (nm)")
ax.annotate("", xy=(3e3, 5.72), xytext=(8, 5.72), arrowprops=dict(arrowstyle="<->", color=S.INK, lw=0.8))
ax.text(155, 5.60, "wavelengths of the heat-carrying phonons", ha="center", va="top", fontsize=7,
        style="italic", color=S.INK)
fig.text(0.05 / W, 5.47 / H, "(a) Scattering layers and their effect on lattice thermal conductivity",
         fontsize=9, va="top", color=S.INK)

# ---------------------------------------------------------- (b) microstructure
fig.text(0.05 / W, 2.78 / H, "(b) Target microstructure (schematic)", fontsize=9, va="top", color=S.INK)
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

ins = axes_in(2.35, 0.92, 1.35, 1.35)
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
ins.set_title("atomic zoom: C leaves its\nsite for SiC (1.4 to 1.7 eV)", fontsize=7, color=S.INK, pad=3)
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

# ------------------------------------------------------------ (c) data panel
fig.text(3.95 / W, 2.78 / H, "(c) Carbon effect against SiC radius", fontsize=9, va="top", color=S.INK)
ax = axes_in(4.45, 0.42, 2.22, 2.05)
R = [2.5, 5, 10, 25, 50, 100, 150]
tags = ["2.5", "5", "10", "25", "50", "100", "150"]
GRAINS = [(1e-7, "0.1 μm", "#B5B5B5"), (3e-7, "0.3 μm", "#6F6F6F"), (5e-7, "0.5 μm", "#1F1F1F")]
rows = [r for r in d["D3_lever_pct_at_yC_0.01"] if r["x"] == 0.2 and r["T"] == 300]
for dm, lab, col in GRAINS:
    r = next(q for q in rows if abs(q["d_m"] - dm) < 1e-12)
    stiff = [r[f"SiC_R{g}nm_stiffness"] for g in tags]
    dens = [r[f"SiC_R{g}nm_density"] for g in tags]
    ax.fill_between(R, stiff, dens, color=col, alpha=0.22, lw=0)
    ax.plot(R, stiff, color=col, lw=1.2, marker="o", ms=3, label=lab)
    ax.plot(R, dens, color=col, lw=0.9, ls="--")
ax.axvspan(100, 300, color=S.LIGHT, lw=0, zorder=0)
ax.text(170, -12, "Zhao et al.\nSiC size", ha="center", va="center", fontsize=7, color=S.INK)
ax.axhline(0, color=S.GREY, lw=0.6)
ax.set_xscale("log")
ax.set_xlim(2.2, 300)
ax.set_xticks(R[:6])
ax.set_xticklabels([str(g) for g in R[:6]])
ax.minorticks_off()
ax.set_xlabel("SiC particle radius R (nm)")
ax.set_ylabel(r"change in $\kappa_L$ per 1 at% C (%)")
ax.legend(loc="lower right", bbox_to_anchor=(0.80, 0.0), title="grain size", title_fontsize=7,
          handlelength=1.4)

S.save(fig, "fig_sigec_layers")
