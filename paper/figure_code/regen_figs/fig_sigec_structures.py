#!/usr/bin/env python3
"""Fig. SiGeC structures, at print size (full width). Same data as
nano_sigec/structures/make_structure_figure.py, four of its six panels;
reads the CIF files in nano_sigec/structures/cif/, the MD box
nano_sigec/structures/md_box/p20.data.gz, nano_sigec/m1c/out/*.json and
nano_sigec/m1c/m1c_summary.json."""
import json

import numpy as np
from ase.io import read
from ase.visualize.plot import plot_atoms

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

ST = S.PROJECT / "nano_sigec" / "structures"
M1C = S.PROJECT / "nano_sigec" / "m1c"
COL = {"Si": "#9DB4C8", "Ge": "#7B4F9E", "C": "#222222"}
MACE = S.SOURCE_COLOURS["mace_md"]
TERS = S.SOURCE_COLOURS["tersoff_md"]
EXP = S.SOURCE_COLOURS["database"]


def colors(at):
    return [COL[s] for s in at.get_chemical_symbols()]


def tag(ax, k, x=-0.25, y=1.02):
    ax.text(x, y, f"({k})", transform=ax.transAxes, fontweight="bold", fontsize=9, va="bottom")


# Four panels: the bulk 3C-SiC render and the screening-pick timeline of the
# earlier six-panel version were removed (the pick timeline is ESI Table S
# "tab:pick", typed from nano_sigec/structures/design_state_timeline.json).
fig = plt.figure(figsize=(S.FULL, 5.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1])

# (a)
ax = fig.add_subplot(gs[0, 0])
at = read(ST / "cif" / "0.2_1_nC4_relaxed.cif")
plot_atoms(at, ax, rotation="10x,-15y,0z", colors=colors(at),
           radii=[0.55 if s == "C" else 0.38 for s in at.get_chemical_symbols()])
ax.set_axis_off()
ax.set_title("Si$_{0.8}$Ge$_{0.2}$ + 4 C on\nlattice sites (MACE-MP)", fontsize=8)
for s, lab in (("Si", "Si"), ("Ge", "Ge"), ("C", "C")):
    ax.scatter([], [], s=18, c=COL[s], label=lab)
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), title="atoms", title_fontsize=7,
          handletextpad=0.1)
tag(ax, "a", -0.02, 1.08)

# (b) slice of the MD box (LAMMPS data file holds the same cell as md_box/p20_relaxed.cif)
ax = fig.add_subplot(gs[0, 1])
box = read(ST / "md_box" / "p20.data.gz", format="lammps-data", atom_style="atomic",
           Z_of_type={1: 14, 2: 32, 3: 6})
p = box.get_positions()
c = box.cell.lengths()
cy, czA = c[1] / 2, c[2] / 4
m = (np.abs(p[:, 1] - cy) < 1.6) & (np.abs(p[:, 2] - czA) < 40)
sym = np.array(box.get_chemical_symbols())[m]
for s in ("Si", "Ge", "C"):
    k = sym == s
    ax.scatter(p[m][k, 0] / 10, (p[m][k, 2] - czA) / 10, s=1.6, c=COL[s], lw=0,
               label={"Si": "Si", "Ge": "Ge", "C": "C"}[s], rasterized=True)
ax.set_aspect("equal")
ax.set_xlabel("$x$ (nm)")
ax.set_ylabel("$z$ (nm)")
ax.grid(False)
ax.set_title("Si$_{0.7}$Ge$_{0.3}$ box, SiC particle\n(Tersoff, 0.3 nm slice)", fontsize=8)
tag(ax, "b", -0.3, 1.0)

# (c) lattice parameter vs x
ax = fig.add_subplot(gs[1, 0])
xs = np.linspace(0, 1, 2)
ax.plot(xs, 5.431 + 0.227 * xs, color=EXP, lw=1.2, label="experiment (Vegard)")
mace = {}
for f in (M1C / "out").glob("*_nC0.json"):
    j = json.load(open(f))
    mace.setdefault(float(j["x"]), []).append(j["a_A"])
for nm in ("Si", "Ge"):
    j = json.load(open(M1C / "out" / f"bulk_{nm}.json"))
    mace.setdefault(0.0 if nm == "Si" else 1.0, []).append(j["a_A"])
X = sorted(mace)
mm = np.array([np.mean(mace[x]) for x in X])
lo = np.array([np.min(mace[x]) for x in X])
hi = np.array([np.max(mace[x]) for x in X])
ax.errorbar(X, mm, yerr=[mm - lo, hi - mm], fmt="o-", ms=3, lw=1, capsize=1.5, color=MACE, label="MACE-MP")
ter = json.load(open(ST / "md_box" / "md_box_lattice.json"))
ax.plot([0, 1], [5.4320, 5.6567], "s", ms=3.5, color=TERS, label="Tersoff")
ax.plot([ter["x"]], [ter["a_A"]], "s", ms=3.5, color=TERS, mfc="white")
ax.set_xlabel("Ge fraction $x$")
ax.set_ylabel("lattice parameter $a$ (Å)")
ax.set_ylim(5.40, 5.90)
ax.legend(loc="upper left")
tag(ax, "c")

# (d) a vs carbon fraction (host Ge fraction on a purple scale, apart from the source colours)
ax = fig.add_subplot(gs[1, 1])
summ = json.load(open(M1C / "m1c_summary.json"))["per_x"]
for xk, c_ in zip(("0", "0.2", "0.5"), ("#C2A5CF", "#9970AB", "#40004B")):
    pts = {}
    for f in (M1C / "out").glob(f"{xk}_*_nC*.json"):
        j = json.load(open(f))
        pts.setdefault(int(j["n_C"]) / 216, []).append(j["a_A"])
    Y = np.array(sorted(pts))
    a0 = summ[xk]["a0_A"]
    A = np.array([np.mean(pts[y]) for y in Y])
    Alo = np.array([np.min(pts[y]) for y in Y])
    Ahi = np.array([np.max(pts[y]) for y in Y])
    ax.errorbar(100 * Y, (A / a0 - 1) * 100, yerr=[(A - Alo) / a0 * 100, (Ahi - A) / a0 * 100],
                fmt="o", ms=3, capsize=1.5, elinewidth=0.6, color=c_, label=f"MACE-MP, $x$ = {xk}")
    yy = np.linspace(0, Y.max(), 2)
    ax.plot(100 * yy, summ[xk]["delta_C"] * yy * 100, color=c_, lw=1)
yy = np.linspace(0, 4 / 216, 2)
ax.plot(100 * yy, -0.394 * yy * 100, "k--", lw=1, label="modified Vegard (fallback)")
ax.set_xlabel("C on lattice sites (at%)")
ax.set_ylabel(r"$\Delta a/a$ (%)")
ax.legend(loc="lower left")
tag(ax, "d")

S.save(fig, "fig_sigec_structures")
