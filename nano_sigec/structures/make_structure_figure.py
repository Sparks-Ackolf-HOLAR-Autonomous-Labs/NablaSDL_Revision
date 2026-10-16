#!/usr/bin/env python3
"""P1 figure: SiGeC crystal structures (from the CIF files in cif/ and
md_box/) and how the structural parameters of the design moved with the
campaign ledger.
(a) MACE-MP-0 relaxed Si0.8Ge0.2 supercell with four substitutional C
(b) MACE-MP-0 relaxed 3C-SiC, where carbon goes (ledger 47-55)
(c) slice through the registered x = 0.3 MD box with an embedded R = 2 nm
    SiC particle and its Si shell (Tersoff-minimised; ledger 78-80)
(d) lattice parameter vs Ge fraction: experiment (Vegard), Tersoff, MACE
(e) lattice parameter vs carbon fraction: Vegard fallback (seq 48) vs the
    converged MACE slope adopted at seq 55
(f) the screening pick (x and SiC radius) and the Ge saving after each
    ledger decision.
Usage: ~/venvs/mace/bin/python make_structure_figure.py"""
import glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ase.io import read
from ase.visualize.plot import plot_atoms

HERE = os.path.dirname(os.path.abspath(__file__))
M1C = os.path.join(HERE, "..", "m1c")
OUT = os.path.join(HERE, "..", "..", "papers", "paper1_j_mater_chem_a", "figures")
COL = {"Si": "#9DB4C8", "Ge": "#7B4F9E", "C": "#222222"}
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 6.5})


def colors(at):
    return [COL[s] for s in at.get_chemical_symbols()]


fig = plt.figure(figsize=(7.0, 5.2))
gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], hspace=0.42, wspace=0.42)

# (a) supercell with substitutional C
ax = fig.add_subplot(gs[0, 0])
at = read(os.path.join(HERE, "cif", "0.2_1_nC4_relaxed.cif"))
r = [0.55 if s == "C" else 0.38 for s in at.get_chemical_symbols()]
plot_atoms(at, ax, rotation="10x,-15y,0z", colors=colors(at), radii=r)
ax.set_axis_off()
ax.set_title("Si$_{0.8}$Ge$_{0.2}$ + 4 C on lattice sites\n(216 sites, MACE relaxed)", fontsize=7)
ax.text(-0.05, 1.22, "(a)", transform=ax.transAxes, fontweight="bold")

# (b) 3C-SiC
ax = fig.add_subplot(gs[0, 1])
at = read(os.path.join(HERE, "cif", "bulk_SiC_relaxed.cif")).repeat((2, 2, 2))
plot_atoms(at, ax, rotation="10x,-15y,0z", colors=colors(at),
           radii=[0.5 if s == "C" else 0.6 for s in at.get_chemical_symbols()])
ax.set_axis_off()
ax.set_title("3C-SiC, where carbon goes\n(−1.44 to −1.68 eV per C)", fontsize=7)
ax.text(-0.05, 1.22, "(b)", transform=ax.transAxes, fontweight="bold")

# (c) MD box slice around particle A
ax = fig.add_subplot(gs[0, 2])
# the CIF (md_box/p20_relaxed.cif) holds the same cell; the LAMMPS data file
# is read here because the ASE CIF parser is slow for 49k atoms
box = read(os.path.join(HERE, "md_box", "p20.data.gz"), format="lammps-data", atom_style="atomic",
           Z_of_type={1: 14, 2: 32, 3: 6})
p = box.get_positions(); c = box.cell.lengths()
cy, czA = c[1] / 2, c[2] / 4
m = (np.abs(p[:, 1] - cy) < 1.6) & (np.abs(p[:, 2] - czA) < 40)
sym = np.array(box.get_chemical_symbols())[m]
for s in ("Si", "Ge", "C"):
    k = sym == s
    ax.scatter(p[m][k, 0] / 10, (p[m][k, 2] - czA) / 10, s=1.6, c=COL[s], lw=0,
               label={"Si": "Si", "Ge": "Ge", "C": "C (in SiC)"}[s])
ax.set_aspect("equal"); ax.set_xlabel("$x$ (nm)"); ax.set_ylabel("$z$ (nm)")
ax.set_title("Si$_{0.7}$Ge$_{0.3}$ MD box, $R$ = 2 nm SiC\n(0.3 nm slice, Tersoff minimised)", fontsize=7)
ax.legend(markerscale=4, frameon=True, framealpha=0.95, edgecolor="none", loc="lower right", handletextpad=0.1, borderpad=0.2)
ax.text(-0.3, 1.13, "(c)", transform=ax.transAxes, fontweight="bold")

# (d) lattice parameter vs x
ax = fig.add_subplot(gs[1, 0])
xs = np.linspace(0, 1, 2)
ax.plot(xs, 5.431 + 0.227 * xs, color="0.5", lw=1, label="experiment (Vegard)")
mace = {}
for f in glob.glob(os.path.join(M1C, "out", "*_nC0.json")):
    j = json.load(open(f)); mace.setdefault(float(j["x"]), []).append(j["a_A"])
for nm in ("Si", "Ge"):
    j = json.load(open(os.path.join(M1C, "out", f"bulk_{nm}.json"))); mace.setdefault(0.0 if nm == "Si" else 1.0, []).append(j["a_A"])
X = sorted(mace)
ax.plot(X, [np.mean(mace[x]) for x in X], "o-", ms=3, color="#C0504D", lw=1, label="MACE-MP-0 (PBE parentage)")
ter = json.load(open(os.path.join(HERE, "md_box", "md_box_lattice.json")))
ax.plot([0, 1], [5.4320, 5.6567], "s", ms=3, color="#4C72B0", label="Tersoff 1989")
ax.plot([ter["x"]], [ter["a_A"]], "s", ms=3, color="#4C72B0", mfc="white")
ax.set_xlabel("Ge fraction $x$"); ax.set_ylabel("lattice parameter $a$ (Å)")
ax.set_ylim(5.40, 5.90); ax.legend(frameon=False, loc="upper left", fontsize=6)
ax.text(-0.3, 1.04, "(d)", transform=ax.transAxes, fontweight="bold")

# (e) a vs carbon fraction
ax = fig.add_subplot(gs[1, 1])
summ = json.load(open(os.path.join(M1C, "m1c_summary.json")))["per_x"]
for xk, c_ in zip(("0", "0.2", "0.5"), ("#8FA9C0", "#3E6A92", "#7B4F9E")):
    pts = {}
    for f in glob.glob(os.path.join(M1C, "out", f"{xk}_*_nC*.json")):
        j = json.load(open(f)); y = int(j["n_C"]) / 216
        pts.setdefault(y, []).append(j["a_A"])
    Y = np.array(sorted(pts)); A = np.array([np.mean(pts[y]) for y in Y])
    a0 = summ[xk]["a0_A"]
    ax.plot(100 * Y, (A / a0 - 1) * 100, "o", ms=3, color=c_, label=f"MACE, $x$ = {xk}")
    yy = np.linspace(0, Y.max(), 2)
    ax.plot(100 * yy, summ[xk]["delta_C"] * yy * 100, color=c_, lw=1)
yy = np.linspace(0, 4 / 216, 2)
ax.plot(100 * yy, -0.394 * yy * 100, "k--", lw=1, label="Vegard (seq 48)")
ax.set_xlabel("C on lattice sites (at%)"); ax.set_ylabel(r"$\Delta a/a$ (%)")
ax.legend(frameon=False, loc="lower left")
ax.text(-0.3, 1.04, "(e)", transform=ax.transAxes, fontweight="bold")

# (f) screening pick along the ledger
ax = fig.add_subplot(gs[1, 2])
T = json.load(open(os.path.join(HERE, "design_state_timeline.json")))["states"]
seq = [s["seq"] for s in T]
xlo = [s["x_pick"][0] for s in T]; xhi = [s["x_pick"][1] for s in T]
ax.fill_between(range(len(T)), xlo, xhi, step="mid", color="#7B4F9E", alpha=0.25)
ax.step(range(len(T)), xlo, where="mid", color="#7B4F9E", lw=1.2)
ax.step(range(len(T)), xhi, where="mid", color="#7B4F9E", lw=1.2)
ax.set_ylim(0, 0.6); ax.set_ylabel("picked $x$", color="#7B4F9E")
ax2 = ax.twinx()
ax2.step(range(len(T)), [s["R_nm"][0] for s in T], where="mid", color="#222222", lw=1.1, ls="--")
ax2.step(range(len(T)), [s["R_nm"][1] for s in T], where="mid", color="#222222", lw=1.1, ls="--")
ax2.set_ylim(0, 6); ax2.set_ylabel("picked SiC radius (nm), dashed")
for i, s in enumerate(T):
    ax.text(i, 0.03, s["ge_saving"], ha="center", fontsize=5.5, rotation=90, va="bottom")
ax.set_xticks(range(len(T))); ax.set_xticklabels(seq, fontsize=6.5)
ax.set_xlabel("ledger entry")
ax.text(-0.3, 1.04, "(f)", transform=ax.transAxes, fontweight="bold")

for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"fig_sigec_structures.{ext}"), dpi=300, bbox_inches="tight")
print("ok")
