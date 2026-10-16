#!/usr/bin/env python3
"""Rebuild selected M1c SiGeC supercells, re-relax them with the same
model, dtype and two-stage optimiser as nano_sigec/m1c/chpc/mace_relax_m1c.py
(imported, not copied), check the energy and lattice parameter against the
committed CHPC result in m1c/out/, and write CIF files of the unrelaxed and
relaxed cells. This is a reproduction of committed results, not new evidence:
no ledger entry is made and no conclusion depends on it.
Usage: ~/venvs/mace/bin/python rebuild_cif.py [device]"""
import json, os, sys, time
import numpy as np
from ase.filters import FrechetCellFilter
from ase.io import write
from ase.optimize import FIRE, LBFGS
from ase.units import GPa
from mace.calculators import mace_mp

HERE = os.path.dirname(os.path.abspath(__file__))
M1C = os.path.join(HERE, "..", "m1c")
sys.path.insert(0, os.path.join(M1C, "chpc"))
import mace_relax_m1c as m  # noqa: E402

TASKS = ["bulk_Si", "bulk_Ge", "bulk_SiC", "0.2_1_nC0", "0.2_1_nC4",
         "0.2_1_maxGe", "0.2_1_minGe", "0.5_1_nC4"]
dev = sys.argv[1] if len(sys.argv) > 1 else "cpu"   # 2026-10-01: GPU full (resident vLLM)
calc = mace_mp(model="medium", default_dtype="float64", device=dev)
out = {}
for task in TASKS:
    atoms, meta = m.build(task)
    write(os.path.join(HERE, "cif", f"{task}_built.cif"), atoms)
    atoms.calc = calc
    filt = FrechetCellFilter(atoms, hydrostatic_strain=True)
    t0 = time.time()
    FIRE(filt, logfile=None).run(fmax=m.F1, steps=m.S1CAP)
    LBFGS(filt, maxstep=0.1, logfile=None).run(fmax=0.005, steps=m.CAP)
    n = len(atoms)
    a = (atoms.get_volume() / (m.NREP ** 3 if n > 8 else 1)) ** (1 / 3)
    E = float(atoms.get_potential_energy())
    f = float(np.linalg.norm(atoms.get_forces(), axis=1).max())
    p = float(-np.trace(atoms.get_stress(voigt=False)) / 3 / GPa)
    ref = json.load(open(os.path.join(M1C, "out", f"{task}.json")))
    write(os.path.join(HERE, "cif", f"{task}_relaxed.cif"), atoms)
    out[task] = {**meta, "n_atoms": n, "a_A": a, "E_eV": E, "fmax": f, "p_GPa": p,
                 "a_chpc_A": ref["a_A"], "E_chpc_eV": ref["E_eV"],
                 "dE_vs_chpc_meV_per_atom": 1000 * (E - ref["E_eV"]) / n,
                 "da_vs_chpc_pct": 100 * (a / ref["a_A"] - 1),
                 "wall_s": time.time() - t0, "device": dev}
    print(task, f"a={a:.4f} (chpc {ref['a_A']:.4f})  dE={out[task]['dE_vs_chpc_meV_per_atom']:.3f} meV/atom  f={f:.4f}", flush=True)
json.dump(out, open(os.path.join(HERE, "rebuild_check.json"), "w"), indent=1)
