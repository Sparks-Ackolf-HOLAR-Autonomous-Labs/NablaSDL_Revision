#!/usr/bin/env python3
"""Stage M1 of the pre-registered SiGeC campaign (sigec_design.json, ledger
seq 46): MACE-MP-0 medium relaxations of substitutional carbon in random
Si(1-x)Ge(x) hosts. One task = one (x, seed) host config, or 'bulk' for the
Si, Ge, 3C-SiC references. Writes one JSON per task into ./out/."""
import json, os, sys, time
import numpy as np
from ase.build import bulk
from ase.filters import ExpCellFilter
from ase.optimize import FIRE
from mace.calculators import mace_mp

CALC = mace_mp(model="medium", default_dtype="float64", device="cpu")
FMAX, STEPS, NREP = 0.01, 600, 3


def relax(atoms):
    atoms = atoms.copy()
    atoms.calc = CALC
    opt = FIRE(ExpCellFilter(atoms, hydrostatic_strain=True), logfile=None)
    conv = bool(opt.run(fmax=FMAX, steps=STEPS))
    f = float(np.abs(atoms.get_forces()).max())
    return atoms, {"E_eV": float(atoms.get_potential_energy()), "V_A3": float(atoms.get_volume()),
                   "fmax": f, "converged": conv and f <= FMAX, "steps": opt.nsteps}


def main(task):
    t0 = time.time()
    os.makedirs("out", exist_ok=True)
    res = {"task": task, "model": "MACE-MP-0 medium float64", "fmax": FMAX}
    if task == "bulk":
        for name, a0, kind in (("Si", 5.431, "diamond"), ("Ge", 5.658, "diamond"), ("SiC", 4.360, "zincblende")):
            at = bulk(name, kind, a=a0, cubic=True)
            r, info = relax(at)
            info["a_A"] = (info["V_A3"]) ** (1 / 3)
            info["n_atoms"] = len(at)
            res[name] = info
    else:
        x, seed = float(task.split("_")[0]), int(task.split("_")[1])
        a_host = 5.431 * (1 - x) + 5.658 * x
        host = bulk("Si", "diamond", a=a_host, cubic=True).repeat((NREP,) * 3)
        n = len(host)
        rng = np.random.default_rng(seed)
        nge = int(round(x * n))
        ge = rng.choice(n, nge, replace=False)
        sym = np.array(["Si"] * n, dtype=object)
        sym[ge] = "Ge"
        host.set_chemical_symbols(list(sym))
        si_sites = np.where(sym == "Si")[0]
        c_order = np.random.default_rng(1000 + seed).permutation(si_sites)
        runs = {}
        for nc in (0, 1, 2, 4):
            at = host.copy()
            s = list(sym)
            for i in c_order[:nc]:
                s[i] = "C"
            at.set_chemical_symbols(s)
            _, info = relax(at)
            info["a_A"] = (info["V_A3"] / NREP ** 3) ** (1 / 3)
            info["n_C"] = nc
            runs[f"nC{nc}"] = info
        res["runs"] = runs
        if x > 0:
            # site preference: count Ge nearest neighbours of each Si site in the ideal host
            from ase.neighborlist import neighbor_list
            i_, j_ = neighbor_list("ij", host, 0.5 * np.sqrt(3) / 2 * a_host + 0.3)
            nge_nn = np.zeros(n, int)
            for a, b in zip(i_, j_):
                if sym[b] == "Ge":
                    nge_nn[a] += 1
            cand = si_sites
            hi = int(cand[np.argmax(nge_nn[cand])])
            lo_c = cand[nge_nn[cand] == 0]
            lo = int(lo_c[0]) if len(lo_c) else int(cand[np.argmin(nge_nn[cand])])
            site = {}
            for lab, idx in (("maxGe", hi), ("minGe", lo)):
                at = host.copy()
                s = list(sym)
                s[idx] = "C"
                at.set_chemical_symbols(s)
                _, info = relax(at)
                info["n_Ge_nn"] = int(nge_nn[idx])
                site[lab] = info
            res["site_pref"] = site
        res.update({"x": x, "seed": seed, "n_sites": n, "n_Ge": nge})
    res["wall_s"] = time.time() - t0
    json.dump(res, open(f"out/{task}.json", "w"), indent=1)
    print("done", task, res["wall_s"])


if __name__ == "__main__":
    main(sys.argv[1])
