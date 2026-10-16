"""Fig. (fig:hypergraph): the evidence hypergraph with true hyperedges.

Each hyperedge is drawn as one closed shaded region (a padded, smoothed
convex hull) over all of its member vertices {paper, regime, method,
system}; hyperedges with identical member sets are merged and the outline
width grows with the number of datapoints sharing that set. Region colour
is the evidence source. Vertex positions come from a spring layout of the
weighted clique expansion (seed 7, as in the earlier render). Reads
pilot/kg/kg_hypergraph.json. Full journal width.
"""
import json
from collections import defaultdict

import networkx as nx
import numpy as np
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, PathPatch
from matplotlib.path import Path as MplPath
from scipy.interpolate import splev, splprep
from scipy.spatial import ConvexHull

S.apply_style()

kg = json.loads((S.PROJECT / "pilot/kg/kg_hypergraph.json").read_text())
vertices, hyperedges = kg["vertices"], kg["hyperedges"]


def source_of(cid):
    cid = str(cid)
    for pref, key in (("DGX", "tersoff_md"), ("CHPC", "tersoff_md"), ("MACE", "mace_md"),
                      ("BTE", "bte_dft"), ("DB-STARRY", "starrydata"), ("DB-", "database")):
        if cid.startswith(pref):
            return key
    return "literature"


def blob_path(pts, pad):
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    ring = pad * np.c_[np.cos(theta), np.sin(theta)]
    cloud = (pts[:, None, :] + ring[None, :, :]).reshape(-1, 2)
    hull = cloud[ConvexHull(cloud).vertices]
    tck, _ = splprep([hull[:, 0], hull[:, 1]], s=0, per=True)
    x, y = splev(np.linspace(0, 1, 120), tck)
    v = np.c_[x, y]
    return MplPath(np.vstack([v, v[:1]]), closed=True)


# merge hyperedges with identical member sets (same rule as the earlier render)
groups = {}
for e in hyperedges:
    key = frozenset(e["members"])
    g = groups.setdefault(key, {"members": e["members"], "count": 0, "source": "literature"})
    g["count"] += 1
    src = source_of(e["provenance"]["corpusId"])
    if src != "literature":
        g["source"] = src

C = nx.Graph()
C.add_nodes_from(vertices)
w = defaultdict(int)
for g in groups.values():
    m = g["members"]
    for i in range(len(m)):
        for j in range(i + 1, len(m)):
            w[(m[i], m[j])] += g["count"]
for (u, v), weight in w.items():
    C.add_edge(u, v, weight=weight)
P = {n: np.asarray(p) for n, p in nx.spring_layout(C, seed=7, k=0.9, weight="weight",
                                                     iterations=300).items()}

fig = plt.figure(figsize=(S.FULL, 4.3), layout="none")
ax = fig.add_axes([0.0, 0.0, 0.63, 1.0])
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(-0.88, 1.06)
ax.set_ylim(-0.93, 1.06)

drawn = sorted(groups.values(),
               key=lambda g: -ConvexHull(np.array([P[m] for m in g["members"]])).volume
               if len(g["members"]) > 2 else 0)
for g in drawn:
    pts = np.array([P[m] for m in g["members"]])
    col = S.SOURCE_COLOURS[g["source"]]
    ax.add_patch(PathPatch(blob_path(pts, 0.035), facecolor=col,
                           alpha=0.05 if g["source"] in ("literature", "starrydata") else 0.14,
                           edgecolor=col, linewidth=0.3 + 0.15 * min(g["count"], 8), zorder=1))

KIND = {"paper": dict(marker="o", s=6, c=S.GREY, label="paper"),
        "regime": dict(marker="o", s=16, c="white", edgecolors=S.INK, linewidths=0.6,
                       label="composition and\ntemperature regime"),
        "method": dict(marker="s", s=22, c=S.INK, label="method"),
        "system": dict(marker="D", s=20, c=S.INK, label="microstructure")}
counts = {}
for kind, st in KIND.items():
    ns = [n for n, v in vertices.items() if v["kind"] == kind]
    counts[kind] = len(ns)
    st = dict(st)
    st.pop("label")
    ax.scatter([P[n][0] for n in ns], [P[n][1] for n in ns], zorder=3, **st)

# label only the method and microstructure vertices, with plain names
NAMES = {"BTE/DFT": "DFT phonon BTE", "MD": "MD", "experiment": "experiment",
         "model-fit": "model fit", "unclear": "unstated method"}
# label placement (offset in points, alignment) chosen so labels do not collide
OFFSET = {"BTE/DFT": (5, 0, "left", "center"), "MD": (-5, 0, "right", "center"),
          "bulk": (4, -3, "left", "top"), "nanowire": (-5, 0, "right", "center"),
          "experiment": (4, 3, "left", "bottom"), "nanostructured": (-4, -3, "right", "top"),
          "other": (4, -3, "left", "top"), "film": (0, -5, "center", "top")}
for n, v in vertices.items():
    if v["kind"] in ("method", "system"):
        dx, dy, ha, va = OFFSET.get(v["name"], (0, 4, "center", "bottom"))
        ax.annotate(NAMES.get(v["name"], v["name"]), P[n], fontsize=7, zorder=4, ha=ha,
                    va=va, xytext=(dx, dy), textcoords="offset points", color=S.INK,
                    bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.75))

# legend panel on the right
lax = fig.add_axes([0.63, 0.0, 0.37, 1.0])
lax.set_axis_off()
src_handles = []
for key in ("literature", "starrydata", "tersoff_md", "bte_dft", "database", "mace_md"):
    n = sum(g["count"] for g in groups.values() if g["source"] == key)
    if n:
        src_handles.append(Patch(fc=S.SOURCE_COLOURS[key], ec=S.SOURCE_COLOURS[key], alpha=0.45,
                                 label=f"{S.SOURCE_NAMES[key]} ({n})"))
leg1 = lax.legend(handles=src_handles, loc="upper left", bbox_to_anchor=(0.0, 0.92),
                  title="Hyperedge region: evidence source\n(datapoints)", title_fontsize=7,
                  alignment="left")
lax.add_artist(leg1)
v_handles = []
for kind, st in KIND.items():
    v_handles.append(Line2D([], [], ls="none", marker=st["marker"],
                            ms=np.sqrt(st["s"]) * 1.0, mfc=st["c"],
                            mec=st.get("edgecolors", st["c"]), mew=0.6,
                            label=f"{st['label']} ({counts[kind]})"))
lax.legend(handles=v_handles, loc="upper left", bbox_to_anchor=(0.0, 0.42),
           title="Vertex", title_fontsize=7, alignment="left")
S.save(fig, "fig_hypergraph")
