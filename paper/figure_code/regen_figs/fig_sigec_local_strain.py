#!/usr/bin/env python3
"""Fig. local strain, at print size (full width). Same data, site choice and
panels as nano_sigec/structures/make_local_strain_figure.py; reads the
MACE-MP-0 cells in nano_sigec/structures/cif/. Does not rewrite
local_strain.json (the original script owns it)."""
import numpy as np
from matplotlib.patches import Rectangle, Circle
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm
from ase.io import read
from ase.neighborlist import neighbor_list

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

CIF = S.PROJECT / "nano_sigec" / "structures" / "cif"
COL = {"Si": "#9DB4C8", "Ge": "#7B4F9E", "C": "#222222"}
RAD = {"Si": 0.34, "Ge": 0.40, "C": 0.24}
CMAP = plt.get_cmap("RdBu_r")
NORM = TwoSlopeNorm(vmin=-18, vcenter=0, vmax=2.5)
EXAG = {"b": 10.0, "c": 10.0, "d": 1.0}

built = read(CIF / "0.2_1_nC4_built.cif")
relax = read(CIF / "0.2_1_nC4_relaxed.cif")
sym = np.array(relax.get_chemical_symbols())
L = relax.cell.lengths()[0]
scale = L / built.cell.lengths()[0]           # Vegard cell -> relaxed cell
a = L / 3                                      # 3x3x3 conventional cells
d_nn = a * np.sqrt(3) / 4                      # ideal NN distance, relaxed cell
ideal = built.get_positions() * scale          # ideal sites in the relaxed cell
pos = relax.get_positions()


def unwrap(p, ref):
    """Image of p closest to ref (cubic cell)."""
    return p - L * np.round((p - ref) / L)


def nn_of(i):
    d = relax.get_distances(i, range(len(relax)), mic=True)
    return [j for j in np.argsort(d)[1:5]]


# choose the zoom sites: a C, then a Ge and a Si in the same (001) slab whose
# first shells hold no C (so (c) and (b) show the plain host)
def in_slab_of(i, zc, half=a / 4 + 0.1):
    dz = ideal[i, 2] - zc
    dz -= L * np.round(dz / L)
    return abs(dz) <= half


def clean(i):
    return all(sym[j] != "C" for j in nn_of(i)) and \
        min(relax.get_distances(i, np.where(sym == "C")[0], mic=True)) > 2 * d_nn


def site_dist(i, j):
    return relax.get_distance(i, j, mic=True)


def pick(iC):
    """Ge and Si sites in the (001) slab of carbon iC, first shells free of C,
    the Ge with no Ge neighbour and the Si with only Si neighbours."""
    zc = ideal[iC, 2]
    cand = [i for i in range(len(relax)) if in_slab_of(i, zc) and site_dist(i, iC) < 0.375 * L]
    ge = [i for i in cand if sym[i] == "Ge" and clean(i) and all(sym[j] == "Si" for j in nn_of(i))]
    if not ge:
        return None
    iGe = min(ge, key=lambda i: site_dist(i, iC))
    si = [i for i in cand if sym[i] == "Si" and clean(i) and all(sym[j] == "Si" for j in nn_of(i))
          and site_dist(i, iGe) > 2 * d_nn]
    if not si:
        return None
    return iGe, min(si, key=lambda i: site_dist(i, iC))


# the C with only Si neighbours whose slab offers clean Ge and Si sites
for iC in np.where(sym == "C")[0]:
    iC = int(iC)
    if all(sym[j] == "Si" for j in nn_of(iC)) and pick(iC):
        iGe, iSi = pick(iC)
        break
zc = ideal[iC, 2]


def in_slab(i):
    return in_slab_of(i, zc)


fig = plt.figure(figsize=(S.FULL, 5.2))
fig.set_layout_engine("none")  # manual layout: zoom panels use fixed aspect and a placed colour bar
gs = fig.add_gridspec(1, 4, width_ratios=[1.45, 1, 1, 1], wspace=0.15,
                      left=0.01, right=0.865, top=0.89, bottom=0.53)
gsb = fig.add_gridspec(1, 2, width_ratios=[1.15, 1], wspace=0.30,
                       left=0.085, right=0.985, top=0.43, bottom=0.115)

# (a) the slab, centred on the C site
ax = fig.add_subplot(gs[0, 0])
ctr = np.mean([unwrap(ideal[i], ideal[iC]) for i in (iC, iGe, iSi)], axis=0)
half_w = 0.5 * L
for i in range(len(relax)):
    if not in_slab(i):
        continue
    p = unwrap(pos[i], ctr) - ctr
    if abs(p[0]) > half_w or abs(p[1]) > half_w:
        continue
    ax.add_patch(Circle(p[:2], RAD[sym[i]] * 0.75, fc=COL[sym[i]], ec="white", lw=0.3, zorder=2))
for i, lab in ((iSi, "b"), (iGe, "c"), (iC, "d")):
    p = unwrap(pos[i], ctr) - ctr
    ax.add_patch(Rectangle((p[0] - 1.85, p[1] - 1.85), 3.7, 3.7, fill=False, ec="#C0504D", lw=0.9, zorder=3))
    ax.text(p[0] + 1.95, p[1] + 1.95, f"({lab})", color="#C0504D", fontsize=6.5, ha="left", va="bottom",
            zorder=4, bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.85))
ax.set_xlim(-half_w, half_w); ax.set_ylim(-half_w, half_w); ax.set_aspect("equal")
ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
for sp in ax.spines.values():
    sp.set_visible(True); sp.set_linewidth(0.6)
ax.set_title("Si$_{0.8}$Ge$_{0.2}$ + 4 C, (001) layer\npair, [001] view (MACE-MP)", fontsize=8)
for s, lab in (("Si", "Si"), ("Ge", "Ge"), ("C", "C")):
    ax.scatter([], [], s=18, c=COL[s], label=lab)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, frameon=False, handletextpad=0.1,
          columnspacing=0.8)
ax.text(0.0, 1.22, "(a)", transform=ax.transAxes, fontweight="bold", fontsize=9)

# (b)-(d) zoom-ins
zoom = {}
for k, (i, lab, title) in enumerate(((iSi, "b", "Si site"), (iGe, "c", "Ge site"), (iC, "d", "C site"))):
    ax = fig.add_subplot(gs[0, k + 1]); ex = EXAG[lab]
    c0 = pos[i]
    nbrs = nn_of(i)
    segs, cols, lens = [], [], []
    for j in nbrs:
        pj = unwrap(pos[j], c0) - c0
        qj = unwrap(ideal[j], ideal[i]) - ideal[i]
        dlen = np.linalg.norm(pj)
        strain = 100 * (dlen / d_nn - 1)
        segs.append([(0, 0), pj[:2]]); cols.append(CMAP(NORM(strain))); lens.append(dlen)
        ax.add_patch(Circle(qj[:2], RAD[sym[j]], fc="none", ec="0.55", lw=0.6, ls="--", zorder=1))
        ax.add_patch(Circle(pj[:2], RAD[sym[j]], fc=COL[sym[j]], ec="white", lw=0.4, zorder=3))
        disp = pj[:2] - qj[:2]
        if np.linalg.norm(disp) > 1e-3:
            ax.annotate("", xy=qj[:2] + ex * disp, xytext=qj[:2],
                        arrowprops=dict(arrowstyle="-|>", color="#C0504D", lw=0.9, mutation_scale=6), zorder=4)
    ax.add_collection(LineCollection(segs, colors=cols, lw=3.2, zorder=2, capstyle="round"))
    ax.add_patch(Circle((0, 0), d_nn * np.sqrt(2 / 3), fc="none", ec="0.75", lw=0.5, ls=":", zorder=0))
    ax.add_patch(Circle((0, 0), RAD[sym[i]], fc=COL[sym[i]], ec="white", lw=0.4, zorder=3))
    mean_d = float(np.mean(lens)); st = 100 * (mean_d / d_nn - 1)
    zoom[lab] = {"site": int(i), "element": str(sym[i]),
                 "neighbours": [str(sym[j]) for j in nbrs],
                 "mean_bond_A": mean_d, "strain_pct": st}
    ax.text(0, -2.05, f"bond {mean_d:.3f} Å\n({st:+.1f}% vs ideal)\narrows " + ("true length" if ex == 1 else f"×{ex:g}"), ha="center", va="top", fontsize=6.5)
    ax.set_xlim(-1.9, 1.9); ax.set_ylim(-2.75, 1.9); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title(title, fontsize=8)
    ax.text(-0.02, 1.1, f"({lab})", transform=ax.transAxes, fontweight="bold", fontsize=9)
cax = fig.add_axes([0.885, 0.60, 0.012, 0.28])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=CMAP), cax=cax)
cb.set_ticks([-15, -10, -5, 0, 2.5]); cb.set_ticklabels(["−15", "−10", "−5", "0", "2.5"]); cb.set_label("bond strain vs ideal (%)", fontsize=7); cb.ax.tick_params(labelsize=7)

# (e) bond lengths by pair type
ax = fig.add_subplot(gsb[0, 0])
i_, j_, d_ = neighbor_list("ijd", relax, 2.75)
groups = {}
for p, q, d in zip(i_, j_, d_):
    if p < q:
        groups.setdefault("–".join(sorted([sym[p], sym[q]], key=lambda s: "SiGeC".index(s))), []).append(d)
order = ["Si–Si", "Si–Ge", "Ge–Ge", "Si–C", "Ge–C"]
order = [o for o in order if o in groups]
bulk = {}
for nm in ("Si", "Ge", "SiC"):
    at = read(CIF / f"bulk_{nm}_relaxed.cif")
    bulk[nm] = float(np.min(at.get_all_distances(mic=True)[np.triu_indices(len(at), 1)]))
rng = np.random.default_rng(0)
for k, o in enumerate(order):
    v = np.array(groups[o])
    ax.scatter(v, k + 0.12 * rng.standard_normal(len(v)), s=4, lw=0,
               c=[CMAP(NORM(100 * (x / d_nn - 1))) for x in v])
    ax.plot([v.mean()] * 2, [k - 0.3, k + 0.3], color="k", lw=1)
    ax.text(2.58, k, f"{v.mean():.3f} Å (n = {len(v)})", va="center", fontsize=6.5)
ax.axvline(d_nn, color="0.4", lw=0.8, ls=":")
for nm, lab in (("Si", "bulk Si"), ("Ge", "bulk Ge"), ("SiC", "3C-SiC")):
    ax.axvline(bulk[nm], color="#4C72B0", lw=0.7, ls="--")
    ax.text(bulk[nm] + (0.012 if nm != "Si" else -0.012), len(order) - 0.45, lab, rotation=90, fontsize=6.5,
            color="#4C72B0", ha="right" if nm == "Si" else "left", va="bottom")
ax.text(d_nn, -0.62, "ideal host", fontsize=6.5, color="0.4", ha="center", va="bottom")
ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
ax.set_ylim(-0.6, len(order) - 0.4); ax.invert_yaxis()
ax.set_xlim(1.85, 2.95); ax.set_xlabel("nearest-neighbour bond length (Å)")
ax.text(-0.16, 1.04, "(e)", transform=ax.transAxes, fontweight="bold", fontsize=9)

# (f) shell-resolved relaxation profile
ax = fig.add_subplot(gsb[0, 1])
shells = np.array([np.sqrt(3) / 4, 1 / np.sqrt(2), np.sqrt(11) / 4, 1.0])


def profile(name, el):
    b = read(CIF / f"{name}_built.cif"); r = read(CIF / f"{name}_relaxed.cif")
    sc = r.cell.lengths()[0] / b.cell.lengths()[0]; ab = b.cell.lengths()[0] / 3
    s = np.array(r.get_chemical_symbols()); out = [[] for _ in shells]
    for c in np.where(s == el)[0]:
        db = b.get_distances(c, range(len(b)), mic=True); dr = r.get_distances(c, range(len(r)), mic=True)
        for k, sh in enumerate(shells * ab):
            m = np.abs(db - sh) < 0.05
            out[k] += list(100 * (dr[m] / (db[m] * sc) - 1))
    return np.array([np.mean(o) for o in out]), np.array([np.std(o) / np.sqrt(len(o)) for o in out]), \
        [len(o) for o in out]


prof = {}
for name, el, c_, lab in (("0.2_1_nC4", "C", "#222222", "around C"),
                          ("0.2_1_nC0", "Ge", "#7B4F9E", "around Ge"),
                          ("0.2_1_nC0", "Si", "#9DB4C8", "around Si")):
    m, se, n = profile(name, el)
    prof[el] = {"cell": name, "shell_strain_pct": m.tolist(), "sem_pct": se.tolist(), "n": n}
    ax.errorbar(shells * a, m, yerr=se, fmt="o-", ms=3.5, lw=1, capsize=1.5, color=c_, label=lab)
ax.axhline(0, color="0.5", lw=0.6)
ax.set_xlabel("ideal distance from the site (Å)")
ax.set_ylabel("shell distance change (%)")
ax.set_xticks(shells * a)
ax.set_xticklabels([f"{x:.2f}\n{k + 1}{['st', 'nd', 'rd', 'th'][k]}" for k, x in enumerate(shells * a)])
ax.legend(frameon=False, loc="lower right")
ins = ax.inset_axes([0.47, 0.32, 0.48, 0.34])
for el, c_ in (("Ge", "#7B4F9E"), ("Si", "#9DB4C8")):
    ins.plot(shells * a, prof[el]["shell_strain_pct"], "o-", ms=2.5, lw=0.8, color=c_)
ins.axhline(0, color="0.5", lw=0.5); ins.set_ylim(-0.6, 1.8)
ins.tick_params(labelsize=6.5); ins.set_xticks([]); ins.set_title("Ge, Si (enlarged)", fontsize=6.5, pad=1.5)
ax.text(-0.17, 1.04, "(f)", transform=ax.transAxes, fontweight="bold", fontsize=9)

S.save(fig, "fig_sigec_local_strain")
