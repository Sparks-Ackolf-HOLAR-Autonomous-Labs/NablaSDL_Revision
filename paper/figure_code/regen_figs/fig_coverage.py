"""Fig. (fig:coverage): where each evidence source sits in composition and temperature.

Every datapoint of the evidence table pilot/kg/extracted_points.json (935 rows)
with a stated Ge fraction is placed on the (x, T) plane; rows that state no
temperature are drawn in a separate strip below the axis. Points are binned
(x to 0.05, T to 50 K) per source; marker area grows with the number of
datapoints in the bin. Marker shape and colour follow the evidence source
(the same colours as every other figure; the two Tersoff MD sources, DGX
Spark and CHPC, share one marker). One column wide.
"""
import json
from collections import Counter

import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

S.apply_style()

pts = json.loads((S.PROJECT / "pilot/kg/extracted_points.json").read_text())


def source_of(p):
    cid = str(p.get("corpusId", ""))
    if cid in ("DGX-MD", "CHPC-MD"):
        return "tersoff_md"
    return {"MACE-MD": "mace_md", "BTE-DFT": "bte_dft", "DB-CITRINE": "database",
            "DB-STARRY": "starrydata"}.get(cid, "literature")


MARK = {"literature": "o", "starrydata": "v", "database": "D", "tersoff_md": "^",
        "mace_md": "s", "bte_dft": "P"}
ORDER = ("starrydata", "literature", "database", "tersoff_md", "bte_dft", "mace_md")
T_NONE = 120.0          # y position of the "temperature not stated" strip

bins = {k: Counter() for k in ORDER}
n_src = Counter()
n_nox = 0
for p in pts:
    x, T = p.get("x_ge"), p.get("T_K")
    if x is None:
        n_nox += 1
        continue
    key = source_of(p)
    n_src[key] += 1
    xb = round(round(float(x) / 0.05) * 0.05, 2)
    tb = T_NONE if T is None else round(float(T) / 50.0) * 50.0
    bins[key][(xb, tb)] += 1


def area(n):
    return 6 + 9 * np.sqrt(n)


fig, ax = plt.subplots(figsize=(S.COL, 3.25))
ax.axhspan(250, 350, color=S.LIGHT, zorder=0, lw=0)
ax.axhline(200, color=S.GREY, lw=0.6, ls="--")
handles = []
for key in ORDER:
    if not bins[key]:
        continue
    xs, ts, ns = zip(*[(xb, tb, n) for (xb, tb), n in bins[key].items()])
    filled = key not in ("starrydata", "literature")
    col = S.SOURCE_COLOURS[key]
    ax.scatter(xs, ts, s=[area(n) for n in ns], marker=MARK[key],
               facecolors=col if filled else "none", edgecolors=col,
               linewidths=0.7, alpha=0.9 if filled else 0.8, zorder=3 if filled else 2)
    handles.append(Line2D([], [], ls="none", marker=MARK[key], ms=5, mew=0.7, color=col,
                          mfc=col if filled else "none",
                          label=f"{S.SOURCE_NAMES[key]} ({n_src[key]})"))
ax.set_xlim(-0.04, 1.04)
tmax = max(tb for k in ORDER for (_, tb) in bins[k])
print("highest temperature bin:", tmax)
ax.set_ylim(60, tmax + 330)
ax.set_yticks([T_NONE, 300, 600, 900, 1200])
ax.set_yticklabels(["not\nstated", "300", "600", "900", "1200"])
ax.set_xlabel(r"Ge fraction $x$ in Si$_{1-x}$Ge$_x$")
ax.set_ylabel("Temperature (K)")
size_h = [Line2D([], [], ls="none", marker="o", mfc="none", mec=S.INK, mew=0.6,
                 ms=np.sqrt(area(n)), label=str(n)) for n in (1, 10, 50)]
leg = fig.legend(handles=handles, loc="outside upper left", ncol=2, handletextpad=0.2,
                 columnspacing=0.6, borderaxespad=0.2)
ax.legend(handles=size_h, title="points per bin", title_fontsize=7, loc="upper right",
          ncol=3, handletextpad=0.1, columnspacing=0.5, borderpad=0.2, borderaxespad=0.1,
          frameon=True, framealpha=0.9, edgecolor="none")
print({k: n_src[k] for k in ORDER}, "no x:", n_nox)
S.save(fig, "fig_coverage")
