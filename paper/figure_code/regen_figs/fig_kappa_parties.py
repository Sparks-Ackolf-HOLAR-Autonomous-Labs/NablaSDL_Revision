"""Fig. (fig:parties): the evidence as it arrives, near room temperature.

(a) every evidence source in 250-350 K; (b) published values alone, by
sample microstructure. Reads the committed evidence table
pilot/kg/extracted_points.json (935 rows). One column wide, panels stacked.
"""
import json
from collections import defaultdict

import paper_fig_style as S
import matplotlib.pyplot as plt

S.apply_style()

pts = json.loads((S.PROJECT / "pilot/kg/extracted_points.json").read_text())


def source_of(p):
    """Map the provenance tag of a row to an evidence source key."""
    cid = str(p.get("corpusId", ""))
    if cid in ("DGX-MD", "CHPC-MD"):
        return "tersoff_md"
    return {"MACE-MD": "mace_md", "BTE-DFT": "bte_dft", "DB-CITRINE": "database",
            "DB-STARRY": "starrydata"}.get(cid, "literature")


def near_room(p):
    T, x, k = p.get("T_K"), p.get("x_ge"), p.get("kappa_W_mK")
    if x is None or k is None or k <= 0:
        return False
    return T is None or 250 <= T <= 350


rows = [p for p in pts if near_room(p)]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(S.COL, 4.9), sharex=True)

# (a) all evidence sources
MARK = {"literature": "o", "starrydata": "v", "database": "D", "tersoff_md": "^",
        "mace_md": "s", "bte_dft": "P"}
groups = defaultdict(list)
for p in rows:
    groups[source_of(p)].append((p["x_ge"], p["kappa_W_mK"]))
for key in ("literature", "starrydata", "database", "tersoff_md", "mace_md", "bte_dft"):
    if not groups[key]:
        continue
    xs, ks = zip(*groups[key])
    ax1.semilogy(xs, ks, ls="none", marker=MARK[key], ms=3.6, mew=0.4, mec="white",
                 color=S.SOURCE_COLOURS[key], alpha=0.85,
                 label=f"{S.SOURCE_NAMES[key]} ({len(xs)})")
ax1.set_ylabel(r"$\kappa$ (W m$^{-1}$ K$^{-1}$)")
ax1.set_title("(a) All evidence sources, 250 to 350 K", loc="left")
ax1.legend(loc="upper right", ncol=2, handletextpad=0.1, columnspacing=0.5, handlelength=1.0,
           borderaxespad=0.2)
ax1.set_ylim(0.2, 2e4)

# (b) published measurements (published values, Starrydata2 curves, experimental
# database) by microstructure: marker = microstructure, colour = evidence source
from matplotlib.lines import Line2D  # noqa: E402

MEASURED = ("literature", "starrydata", "database")
SHAPE = {"bulk": "o", "nanostructured": "P", "nanowire": "X", "film": "^",
         "amorphous": "s", "superlattice": "D", "other": "."}
by_sys = defaultdict(list)
for p in rows:
    src = source_of(p)
    if src in MEASURED:
        by_sys[(p.get("system") or "other", src)].append((p["x_ge"], p["kappa_W_mK"]))
handles = []
for name in ("bulk", "nanostructured", "nanowire", "film", "amorphous", "superlattice", "other"):
    n = 0
    for src in MEASURED:
        if not by_sys[(name, src)]:
            continue
        xs, ks = zip(*by_sys[(name, src)])
        n += len(xs)
        ax2.semilogy(xs, ks, ls="none", marker=SHAPE[name], ms=4.2 if name != "other" else 5,
                     mew=0.4, mec="white", color=S.SOURCE_COLOURS[src], alpha=0.9)
    if n:
        handles.append(Line2D([], [], ls="none", marker=SHAPE[name], ms=4.2, color=S.INK,
                              mec="white", mew=0.4, label=f"{name} ({n})"))
ax2.set_xlabel(r"Ge fraction $x$ in Si$_{1-x}$Ge$_x$")
ax2.set_ylabel(r"$\kappa$ (W m$^{-1}$ K$^{-1}$)")
ax2.set_title("(b) Measured values by microstructure", loc="left")
ax2.legend(handles=handles, loc="upper right", ncol=2, handletextpad=0.1, columnspacing=0.6, handlelength=1.0,
           borderaxespad=0.2)
ax2.set_ylim(0.2, 6e4)
ax2.set_xlim(-0.04, 1.04)

S.save(fig, "fig_kappa_parties")
