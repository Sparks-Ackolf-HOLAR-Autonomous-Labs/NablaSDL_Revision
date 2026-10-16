#!/usr/bin/env python3
"""Bond angle distributions (BAD) for three structure sets in mat_theory.
(1) MD: Tersoff Si-Ge rebuilds of the Phase C production probes (md/):
    amorphous N2/N3 (A300, A700), near-melting N0/N1 (M1500, M1450) and
    crystal rows at the probe compositions (X300, X700); 2 seeds x 11 frames.
(2) MACE: the M1c cells in nano_sigec/structures/cif (C-, Ge-, Si-centred).
(3) SiC/SiGe interface: the x = 0.3 embedded-SiC Tersoff box (p20.data.gz),
    angles binned by distance to the nearest C atom.
Angles j-i-k over first-shell neighbours (cutoff below the second shell).
Writes bad_results.json. Usage: ~/venvs/mace/bin/python analyze_bad.py"""
import json, os, glob, gzip
import numpy as np
from ase.io import read
from ase.neighborlist import neighbor_list
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
TET = np.degrees(np.arccos(-1 / 3))
BINS = np.linspace(0, 180, 181)


def angles(atoms, cut, centres=None):
    """Return (centre index, angle in deg) for every j-i-k triple, plus
    coordination numbers."""
    i, j, D = neighbor_list("ijD", atoms, cut)
    n = len(atoms)
    order = np.argsort(i, kind="stable"); i, j, D = i[order], j[order], D[order]
    starts = np.searchsorted(i, np.arange(n + 1))
    cn = np.diff(starts)
    ci, th = [], []
    ids = range(n) if centres is None else centres
    for a in ids:
        v = D[starts[a]:starts[a + 1]]
        m = len(v)
        if m < 2:
            continue
        u = v / np.linalg.norm(v, axis=1)[:, None]
        c = np.clip(u @ u.T, -1, 1)
        iu = np.triu_indices(m, 1)
        t = np.degrees(np.arccos(c[iu]))
        th.append(t); ci.append(np.full(len(t), a))
    if not th:
        return np.array([], int), np.array([]), cn
    return np.concatenate(ci), np.concatenate(th), cn


def summ(th, cn=None):
    out = {"n_angles": int(len(th)), "mean_deg": float(th.mean()), "std_deg": float(th.std()),
           "rms_dev_from_tet_deg": float(np.sqrt(np.mean((th - TET) ** 2))),
           "frac_outside_tet_pm20": float(np.mean(np.abs(th - TET) > 20)),
           "frac_below_80": float(np.mean(th < 80)),
           "hist": np.histogram(th, BINS, density=True)[0].round(6).tolist()}
    if cn is not None:
        out["coordination"] = {str(k): float(np.mean(cn == k)) for k in range(2, 7)}
        out["mean_cn"] = float(cn.mean())
    return out


def read_dump(path):
    """Frames from a LAMMPS custom dump (id type x y z), orthorhombic box."""
    from ase import Atoms
    frames = []
    with gzip.open(path, "rt") as f:
        lines = f.read().split("\n")
    k = 0
    while k < len(lines) and lines[k].startswith("ITEM: TIMESTEP"):
        n = int(lines[k + 3])
        lo_hi = [list(map(float, lines[k + 5 + d].split()[:2])) for d in range(3)]
        cell = [h - l for l, h in lo_hi]
        arr = np.array([l.split() for l in lines[k + 9:k + 9 + n]], float)
        sym = np.where(arr[:, 1] == 1, "Si", "Ge")
        frames.append(Atoms(symbols=list(sym), positions=arr[:, 2:5] - [l for l, _ in lo_hi], cell=cell, pbc=True))
        k += 9 + n
    return frames


def main():
    res = {"tetrahedral_deg": TET, "bins_deg": BINS.tolist()}

    # (1) MD probes: per-frame descriptors and pooled BAD
    CUT_MD = 2.95   # first g(r) minimum of Tersoff SiGe (between 2.35-2.45 and 3.84 A)
    md = {}
    for path in sorted(glob.glob(os.path.join(HERE, "md", "*.dump.gz"))):
        tag = os.path.basename(path)[:-8]
        fr = read_dump(path)
        per, pool, cns = [], [], []
        for at in fr:
            _, th, cn = angles(at, CUT_MD)
            per.append({"std_deg": float(th.std()), "frac_outside_tet_pm20": float(np.mean(np.abs(th - TET) > 20)),
                        "frac_cn4": float(np.mean(cn == 4))})
            pool.append(th); cns.append(cn)
        pe = None
        for l in open(path[:-8] + ".log"):
            if l.startswith("MPT_PE_SAMPLE"):
                pe = float(l.split()[1])
        md[tag] = {"frames": per, "pe_eV_atom": pe, **summ(np.concatenate(pool), np.concatenate(cns))}
    res["md_probes"] = md

    # (2) MACE cells, by centre element and for the C-free reference
    mace = {}
    for name in ("0.2_1_nC4_relaxed", "0.2_1_nC0_relaxed", "0.5_1_nC4_relaxed", "bulk_Si_relaxed", "bulk_SiC_relaxed"):
        at = read(os.path.join(HERE, "..", "nano_sigec", "structures", "cif", name + ".cif"))
        sym = np.array(at.get_chemical_symbols())
        ci, th, cn = angles(at, 2.75)
        d = {"all": summ(th, cn)}
        for el in ("Si", "Ge", "C"):
            sel = sym[ci] == el
            if sel.any():
                d[el + "-centred"] = summ(th[sel])
        # Si atoms bonded to C: the angles they make with their other neighbours
        if "C" in sym:
            i, j = neighbor_list("ij", at, 2.75)
            si_nC = sorted({int(a) for a, b in zip(i, j) if sym[a] == "Si" and sym[b] == "C"})
            sel = np.isin(ci, si_nC)
            d["Si-next-to-C-centred"] = summ(th[sel])
        mace[name] = d
    res["mace_cells"] = mace

    # (3) embedded-SiC Tersoff box: angles vs distance from the nearest C
    with gzip.open(os.path.join(HERE, "..", "nano_sigec", "structures", "md_box", "p20.data.gz"), "rt") as f:
        txt = f.read()
    from io import StringIO
    from ase.io.lammpsdata import read_lammps_data
    box = read_lammps_data(StringIO(txt), Z_of_type={1: 14, 2: 32, 3: 6}, style="atomic")
    sym = np.array(box.get_chemical_symbols())
    ci, th, cn = angles(box, 2.95)
    iC = np.where(sym == "C")[0]
    tree = cKDTree(box.positions[iC] % box.cell.lengths(), boxsize=box.cell.lengths())
    dC, _ = tree.query(box.positions % box.cell.lengths())
    inter = {}
    edges = [(0.0, 0.01, "C atoms (SiC core)"), (0.01, 2.2, "Si bonded to C"), (2.2, 4.0, "first host shell"),
             (4.0, 6.0, "second host shell"), (6.0, 10.0, "host 6-10 A"), (10.0, 1e9, "host > 10 A")]
    for lo, hi, lab in edges:
        atoms_in = np.where((dC >= lo) & (dC < hi))[0]
        sel = np.isin(ci, atoms_in)
        inter[lab] = {"n_atoms": int(len(atoms_in)), **summ(th[sel], cn[atoms_in])}
    res["sic_interface_x0.3"] = inter

    json.dump(res, open(os.path.join(HERE, "bad_results.json"), "w"), indent=1)
    for k, v in md.items():
        print(k, round(v["pe_eV_atom"], 3), round(v["std_deg"], 2), round(v["frac_outside_tet_pm20"], 4), round(v["mean_cn"], 3), v["coordination"])
    for k, v in mace.items():
        print(k, {kk: (round(vv["mean_deg"], 2), round(vv["std_deg"], 2)) for kk, vv in v.items()})
    for k, v in inter.items():
        print(k, v["n_atoms"], round(v["mean_deg"], 2), round(v["std_deg"], 2), round(v["frac_outside_tet_pm20"], 4), round(v["mean_cn"], 3))


if __name__ == "__main__":
    main()
