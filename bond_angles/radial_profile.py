#!/usr/bin/env python3
"""Bond-angle spread against distance from the centre of each embedded SiC
particle in the x = 0.3 Tersoff box (R = 20 A). Appends 'sic_radial' to
bad_results.json. Usage: ~/venvs/mace/bin/python radial_profile.py"""
import json, os, gzip
from io import StringIO
import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from ase.io.lammpsdata import read_lammps_data
from analyze_bad import angles, TET

HERE = os.path.dirname(os.path.abspath(__file__))
with gzip.open(os.path.join(HERE, "..", "nano_sigec", "structures", "md_box", "p20.data.gz"), "rt") as f:
    box = read_lammps_data(StringIO(f.read()), Z_of_type={1: 14, 2: 32, 3: 6}, atom_style="atomic")
L = box.cell.lengths(); P = box.positions % L
sym = np.array(box.get_chemical_symbols())
iC = np.where(sym == "C")[0]
t = cKDTree(P[iC], boxsize=L)
n, lab = connected_components(t.sparse_distance_matrix(t, 3.3), directed=False)
cent = []
for k in range(n):
    q = P[iC[lab == k]]
    ang = 2 * np.pi * q / L          # periodic mean
    c = (np.arctan2(np.sin(ang).mean(0), np.cos(ang).mean(0)) % (2 * np.pi)) * L / (2 * np.pi)
    cent.append(c)
cent = np.array(cent)
d = P[:, None, :] - cent[None]
d -= L * np.round(d / L)
r = np.linalg.norm(d, axis=2).min(1)
ci, th, cn = angles(box, 2.95)
edges = np.arange(0, 32.5, 1.0)
prof = []
for lo, hi in zip(edges[:-1], edges[1:]):
    a = np.where((r >= lo) & (r < hi))[0]
    s = np.isin(ci, a)
    if s.sum() < 20:
        continue
    prof.append({"r_lo_A": float(lo), "r_hi_A": float(hi), "n_atoms": int(len(a)),
                 "frac_C": float(np.mean(sym[a] == "C")), "std_deg": float(th[s].std()),
                 "frac_outside_tet_pm20": float(np.mean(np.abs(th[s] - TET) > 20)),
                 "mean_cn": float(cn[a].mean())})
res = json.load(open(os.path.join(HERE, "bad_results.json")))
res["sic_radial"] = {"n_particles": int(n), "particle_C_counts": np.bincount(lab).tolist(),
                     "nominal_R_A": 20.0, "profile": prof}
json.dump(res, open(os.path.join(HERE, "bad_results.json"), "w"), indent=1)
print(n, np.bincount(lab))
for p in prof:
    print(p["r_lo_A"], p["n_atoms"], round(p["frac_C"], 2), round(p["std_deg"], 2), round(p["frac_outside_tet_pm20"], 3), round(p["mean_cn"], 3))
