#!/usr/bin/env python3
"""Gate G0 of implant_design.json (ledger seq 151): RustBCA ranges for the registered
cross-check recipes, same targets and inputs as the install smoke test.
Usage: python3 rustbca_crosscheck.py /path/to/RustBCA"""
import hashlib, json, os, subprocess, sys, pathlib
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
reg = (HERE / "PREREGISTERED_SHA256").read_text().split()[0]
if hashlib.sha256((HERE / "implant_design.json").read_bytes()).hexdigest() != reg:
    sys.exit("implant_design.json changed after registration")
D = json.loads((HERE / "implant_design.json").read_text())
sys.path.insert(0, str(HERE.parent.parent / "second_system/implant_srim/rustbca"))
import smoke as S  # noqa: E402
S.EL.update({"He": (2, 4.003, 0.0, 1.0), "Kr": (36, 83.798, 0.0, 1.0)})
out = HERE / "rustbca_run"; out.mkdir(exist_ok=True)
res = {}
for ion, e, x in D["recipes"]["rustbca_crosscheck"]:
    name = f"{ion}_{'Si' if x == 0 else f'Si{1 - x:g}Ge{x:g}'}_{e}keV"
    f = out / f"{name}.toml"
    f.write_text(S.toml(name, ion, e * 1e3, S.target(x), n_ions=20000).replace("num_threads = 8", "num_threads = 4"))
    subprocess.run([sys.argv[1], "1D", f.name], cwd=out, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dep = np.loadtxt(out / f"{name}_deposited.output", delimiter=",", ndmin=2)
    x_nm = dep[:, 2] * 1e3
    res[name] = {"ions_stopped": int(len(x_nm)), "Rp_nm": round(float(x_nm.mean()), 1), "dRp_nm": round(float(x_nm.std()), 1)}
    print(name, res[name], flush=True)
    for p in out.glob(f"{name}_*.output"):
        if p.stat().st_size > 2_000_000:
            p.unlink()  # keep the repo small; the summary carries the range statistics
(HERE / "rustbca_ranges.json").write_text(json.dumps(res, indent=1))
