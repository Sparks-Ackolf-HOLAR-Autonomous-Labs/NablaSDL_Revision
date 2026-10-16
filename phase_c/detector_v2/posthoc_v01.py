#!/usr/bin/env python3
"""POST-HOC (not registered): why did the V01 harm vanish under v2? Rerun
the D2 detector on the V01 trials with only the amorphous probe rows
(N2, N3) removed, and with only the domain/premelting rows removed."""
import json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "production")); sys.path.insert(0, os.path.join(HERE, "..", "production", "fault_catalog"))
import detector as v1, fault_study as FS, inject_faults as IF
v1.DUP_MODE = "design"
rows = json.load(open(os.path.join(HERE, "..", "production", "results", "production_rows.json")))
drop = {"amorphous probes removed": lambda r: r["run_id"][:2] not in ("N2", "N3"),
        "x>0.9 and T>=0.85 T_sol removed": lambda r: r["x"] <= 0.9 and r["T"] < 0.85 * v1.solidus(r["x"]),
        "nothing removed (D2)": lambda r: True}
out = {}
for name, keep in drop.items():
    base = [r for r in rows if keep(r)]
    bl = frozenset((o["op"], tuple(sorted(o["target_runs"]))) for o in v1.detect(base)["ops"])
    c = Counter()
    for ts in IF.trial_seeds("V01", 50):
        rt, tr = IF.inject(base, "V01", ts)
        s = FS.score(v1.detect(rt), tr, rt, bl)
        c[s.get("outcome_A_adj", s["outcome_A"])] += 1
    out[name] = dict(c); print(name, dict(c))
json.dump(out, open(os.path.join(HERE, "posthoc_v01.json"), "w"), indent=1)
