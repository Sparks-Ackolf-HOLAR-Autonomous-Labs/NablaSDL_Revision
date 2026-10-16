"""Render the evidence hypergraph with true hyperedges.

The earlier figure drew the bipartite star expansion (one grey node per
datapoint, plain pairwise edges), which reads as an ordinary graph. Here
each hyperedge is drawn as what it is: a single closed region (a padded,
spline-smoothed convex hull) enclosing all of its member vertices
{paper, regime, method, system}. Hyperedges with identical member sets are
merged into one region whose outline width scales with the datapoint count,
and regions are colored by evidence party (literature vs DGX-MD).

Vertex positions come from a spring layout of the weighted clique expansion,
so co-membered vertices sit near each other and the regions stay compact.
The bipartite .graphml stays as the algorithmic representation; this file
only concerns the picture.

Run:  python render_hypergraph.py <kg_dir>
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from scipy.interpolate import splev, splprep
from scipy.spatial import ConvexHull

KIND_COLORS = {"paper": "#1f77b4", "regime": "#d62728",
               "method": "#2ca02c", "system": "#9467bd"}
PARTY_COLORS = {"literature": "#4c78a8", "DGX-MD": "#e45756",
                "CHPC-MD": "#59a14f", "MACE-MD": "#b279a2",
                "BTE-DFT": "#eeca3b", "DB-CITRINE": "#ff9da6",
                "DB-STARRY": "#9d755d"}


def blob_path(pts: np.ndarray, pad: float) -> MplPath:
    """Closed smooth outline around member points: convex hull of small
    circles centered on each member, then a periodic spline through it."""
    theta = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    ring = pad * np.c_[np.cos(theta), np.sin(theta)]
    cloud = (pts[:, None, :] + ring[None, :, :]).reshape(-1, 2)
    hull = cloud[ConvexHull(cloud).vertices]
    tck, _ = splprep([hull[:, 0], hull[:, 1]], s=0, per=True)
    x, y = splev(np.linspace(0, 1, 120), tck)
    verts = np.c_[x, y]
    return MplPath(np.vstack([verts, verts[:1]]),
                   closed=True)


def render(kg_dir: Path) -> None:
    kg = json.loads((kg_dir / "kg_hypergraph.json").read_text())
    vertices, hyperedges = kg["vertices"], kg["hyperedges"]

    # Merge hyperedges with identical member sets; keep party + multiplicity.
    groups: dict[frozenset, dict] = {}
    for e in hyperedges:
        key = frozenset(e["members"])
        g = groups.setdefault(key, {"members": e["members"], "count": 0,
                                    "party": "literature"})
        g["count"] += 1
        cid = str(e["provenance"]["corpusId"])
        for pref, party in (("DGX", "DGX-MD"), ("CHPC", "CHPC-MD"),
                            ("MACE", "MACE-MD"), ("BTE", "BTE-DFT"),
                            ("DB-STARRY", "DB-STARRY"),
                            ("DB-", "DB-CITRINE")):
            if cid.startswith(pref):
                g["party"] = party
                break

    # Layout on the weighted clique expansion of the vertices only.
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
    pos = nx.spring_layout(C, seed=7, k=0.9, weight="weight",
                           iterations=300)
    P = {n: np.asarray(p) for n, p in pos.items()}

    fig, ax = plt.subplots(figsize=(15, 11))

    # Hyperedge regions, largest first so small ones stay visible on top.
    drawn = sorted(groups.values(),
                   key=lambda g: -ConvexHull(
                       np.array([P[m] for m in g["members"]])).volume
                   if len(g["members"]) > 2 else 0)
    for g in drawn:
        pts = np.array([P[m] for m in g["members"]])
        color = PARTY_COLORS[g["party"]]
        path = blob_path(pts, pad=0.035)
        ax.add_patch(PathPatch(path, facecolor=color,
                               alpha=0.06 if g["party"] == "literature"
                               else 0.16,
                               edgecolor=color,
                               linewidth=0.7 + 0.35 * min(g["count"], 8),
                               zorder=1))

    # Vertices on top, colored by kind.
    for kind, color in KIND_COLORS.items():
        ns = [n for n, v in vertices.items() if v["kind"] == kind]
        ax.scatter([P[n][0] for n in ns], [P[n][1] for n in ns],
                   s=60 if kind == "paper" else 170, c=color,
                   edgecolors="white", linewidths=0.8, zorder=3,
                   label=f"{kind} ({len(ns)})")
    for n, v in vertices.items():
        if v["kind"] in ("regime", "method", "system"):
            ax.annotate(v["name"], P[n], fontsize=7.5, zorder=4,
                        ha="center", va="center",
                        xytext=(0, 9), textcoords="offset points")

    for party, color in PARTY_COLORS.items():
        n = sum(g["count"] for g in groups.values() if g["party"] == party)
        if n:
            ax.fill([], [], color=color, alpha=0.25,
                    label=f"hyperedge region: {party} ({n} datapoints)")
    ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax.set_title(
        "SiGe kappa evidence hypergraph: each shaded region is one hyperedge "
        "over {paper, regime, method, system}\n"
        f"{len(hyperedges)} datapoints in {len(groups)} distinct hyperedge "
        "member sets; outline width = datapoints sharing that member set")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(kg_dir / "kg_hypergraph.png", dpi=150)
    plt.close(fig)
    print(f"wrote kg_hypergraph.png: {len(groups)} regions, "
          f"{len(hyperedges)} hyperedges, {len(vertices)} vertices")


if __name__ == "__main__":
    render(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
