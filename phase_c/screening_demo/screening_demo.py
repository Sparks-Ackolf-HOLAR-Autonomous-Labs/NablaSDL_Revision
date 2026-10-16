#!/usr/bin/env python3
"""P1 screening-decision demo (audit doc section 2).

Materials decision: a thermoelectric designer wants the Si(1-x)Ge(x)
composition window that minimizes lattice thermal conductivity kappa at
1100 K (also 300 K and 700 K) and a ranking of candidates
x in {0.05, 0.10, ..., 0.95}. Three ways of making the call:

 (a) NAIVE-LIT+DB: one fit of 1/kappa = a + b x + c x^2 + d T on the
     literature party exactly as first extracted (67 rows, no second-
     extractor corrections, no sample-class labels) plus the Citrine
     database party. Rows without T get T = 300 K (the usual naive
     "room temperature" assumption); rows without x cannot be used.
 (b) NAIVE-POOLED-ALL: the same fit on every party's points pooled with
     no party or scope distinction (literature as extracted, Citrine,
     CHPC-MD raw finite-size rows, DGX-MD, MACE-MD, BTE-DFT, and the
     42 extrapolated Tersoff bulk series behind the final law).
 (c) SCOPE-AWARE: the final law's shape (phase_c/final_law/final_law.json;
     HG-SR on the post-operation CHPC-MD state, Tersoff-parented), put on
     an absolute scale by the first-principles BTE-DFT party with a
     per-regime multiplicative correction r(x, T) = kappa_BTE / kappa_law
     (log-linear in x between the BTE nodes inside the domain, flat
     beyond the outermost node), and refusing any candidate outside the
     validity domain x in [0.05, 0.90], T <= 0.85 T_solidus(x). The
     literature enters only as the corrected, bulk-scope rows (ledger
     seq 20-23 plus the stage-0 sample split), and only as a check.

Also: bootstrap (500 row resamples, seeded) of the argmin for each
approach, and an ablation adding the ledgered revisions one at a time.
The ledger is read, never written. CPU only, about a minute.
Usage: ~/mat_theory_pilot/venv/bin/python screening_demo.py
"""
import json
import os
import sys
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.abspath(os.path.join(HERE, ".."))
MT = os.path.abspath(os.path.join(PC, ".."))
sys.path.insert(0, os.path.join(PC, "sr_compare"))
sys.path.insert(0, os.path.join(PC, "production"))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
import hgsr  # noqa: E402
from detector import solidus  # noqa: E402
from ledger import leaf_hash  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)
SEED = 20260929
N_BOOT = 500
TEMPS = (300.0, 700.0, 1100.0)
CAND = np.round(np.arange(0.05, 0.951, 0.05), 2)     # designer's candidates
FINE = np.round(np.arange(0.05, 0.9501, 0.005), 3)   # for continuous argmin
WINDOW = 0.10                                         # within 10% of the minimum
X_MIN, X_MAX_LAW = 0.05, 0.90


def rel(p):
    return os.path.relpath(p, MT)


# ---------------------------------------------------------------- data ----
KG_PATH = os.path.join(MT, "pilot", "kg", "extracted_points.json")
kg = json.load(open(KG_PATH))
law = json.load(open(os.path.join(PC, "final_law", "final_law.json")))
p5 = json.load(open(os.path.join(MT, "party5_databases", "party5_points.json")))
split = json.load(open(os.path.join(PC, "chd", "split_decision.json")))
ledger = [json.loads(l) for l in open(os.path.join(PC, "ledger_campaign.jsonl"))]

lit_idx = [i for i, q in enumerate(kg) if str(q.get("corpusId")).isdigit()]
assert len(lit_idx) == 67 and lit_idx == list(range(67))

# ledgered literature operations (read-only)
ops = {e["payload"]["op_id"]: e for e in ledger
       if e.get("payload", {}).get("op_id", "").endswith("2026-09-29")
       and "literature" in e["payload"]["op_id"]}
op_nonsige = ops["scope-limit-literature-non-SiGe-2026-09-29"]
op_forget = ops["forget-literature-absent-values-2026-09-29"]
op_correct = ops["correct-literature-row34-x-2026-09-29"]
op_quar = ops["quarantine-literature-unattributable-2026-09-29"]
# the ledger addresses rows by leaf_hash; verify the kg_index mirrors agree
for e in (op_nonsige, op_forget, op_correct, op_quar):
    assert [leaf_hash(kg[i]) for i in e["payload"]["kg_index"]] == e["payload"]["rows"]
NON_SIGE = set(op_nonsige["payload"]["kg_index"])
FORGET = set(op_forget["payload"]["kg_index"])
QUAR = set(op_quar["payload"]["kg_index"])
CORRECT = {i: (op_correct["payload"]["field"], op_correct["payload"]["to"])
           for i in op_correct["payload"]["kg_index"]}
hash2i = {leaf_hash(kg[i]): i for i in lit_idx}
BULK_SCOPE = {hash2i[h] for h in split["scopes"]["literature-bulk"]["row_ids"]}
SEQS = {k: v["seq"] for k, v in ops.items()}
SEQ_CORNER = [e["seq"] for e in ledger
              if e.get("payload", {}).get("op_id") == "scope-limit-alloy-law-x-le-0.90-2026-09-29"]


def lit_rows(forget=False, correct=False, quarantine=False, bulk_only=False,
             x_cap=None, impute_T=True):
    """Literature party rows under a chosen set of ledgered operations."""
    out = []
    for i in lit_idx:
        q = dict(kg[i])
        if forget and (i in NON_SIGE or i in FORGET):
            continue
        if correct and i in CORRECT:
            f, v = CORRECT[i]
            q[f] = v
        if quarantine and i in QUAR:
            continue
        if bulk_only and i not in BULK_SCOPE:
            continue
        if q.get("x_ge") is None or q.get("kappa_W_mK") is None:
            continue
        T = q.get("T_K")
        if T is None:
            if not impute_T:
                continue
            T = 300.0
        x = float(q["x_ge"])
        if x_cap is not None and x > x_cap + 1e-9:
            continue
        out.append({"x": x, "T": float(T), "kappa": float(q["kappa_W_mK"]),
                    "party": "literature", "kg": i})
    return out


def citrine_rows(x_cap=None):
    return [{"x": float(q["x_ge"]), "T": float(q["T_K"]), "kappa": float(q["kappa_W_mK"]),
             "party": "DB-CITRINE"} for q in p5
            if x_cap is None or float(q["x_ge"]) <= x_cap + 1e-9]


def other_party_rows():
    rows = []
    for q in kg:
        cid = str(q.get("corpusId"))
        if cid.isdigit() or cid == "DB-CITRINE":
            continue
        rows.append({"x": float(q["x_ge"]), "T": float(q["T_K"]),
                     "kappa": float(q["kappa_W_mK"]), "party": cid})
    for r in law["bulk_rows"]:
        rows.append({"x": r["x"], "T": r["T"], "kappa": r["kappa"],
                     "party": "CHPC-MD-bulk-series"})
    return rows


BTE = {}
for q in kg:
    if q.get("corpusId") == "BTE-DFT":
        BTE[(round(float(q["x_ge"]), 3), float(q["T_K"]))] = float(q["kappa_W_mK"])


def in_domain(x, T):
    return (X_MIN - 1e-9 <= x <= X_MAX_LAW + 1e-9) and (300 - 1e-9 <= T <= 0.85 * solidus(x))


# -------------------------------------------------------------- models ----
def fit_naive(rows):
    """OLS of 1/kappa on (1, x, x^2, T); every row weighted equally."""
    X = np.array([[1.0, r["x"], r["x"] ** 2, r["T"]] for r in rows])
    y = np.array([1.0 / r["kappa"] for r in rows])
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    return c


def naive_kappa(c, x, T):
    inv = c[0] + c[1] * x + c[2] * x ** 2 + c[3] * T
    return np.where(inv > 0, 1.0 / np.where(inv > 0, inv, 1.0), np.nan)


LAW_TERMS = law["bulk_law_terms"]
BASIS = {b[0]: b[2] for b in hgsr.make_basis(["x", "T"])}


def law_kappa(terms, x, T):
    x = np.atleast_1d(np.asarray(x, float))
    d = {"x": x, "T": np.full_like(x, float(T))}
    inv = sum(c * BASIS[n](d) for n, c in terms.items())
    return np.where(inv > 0, 1.0 / np.where(inv > 0, inv, 1.0), np.nan)


def calib_nodes(T, drop=None):
    """BTE nodes usable for calibration at temperature T (inside the law domain)."""
    return sorted(x for (x, t) in BTE if t == T and in_domain(x, T) and x != drop)


def calib_factor(terms, x, T, drop=None):
    """Per-regime multiplicative scope correction r = kappa_BTE / kappa_law,
    log-linear in x between BTE nodes, flat beyond the outermost node."""
    nodes = calib_nodes(T, drop)
    lr = [np.log(BTE[(xn, T)] / float(law_kappa(terms, xn, T)[0])) for xn in nodes]
    return np.exp(np.interp(np.atleast_1d(x), nodes, lr))


def scope_kappa(terms, x, T, calibrate=True, refuse=True, drop=None):
    x = np.atleast_1d(np.asarray(x, float))
    k = law_kappa(terms, x, T)
    if calibrate:
        k = k * calib_factor(terms, x, T, drop)
    if refuse:
        k = np.where([in_domain(xi, T) for xi in x], k, np.nan)
    return k


# ----------------------------------------------------------- decisions ----
def decide(fn, T, domain_check=True):
    """fn(x_array) -> kappa (nan = refused/unphysical). Returns the decision."""
    kf = fn(FINE)
    kc = fn(CAND)
    ok = np.isfinite(kf)
    if not ok.any():
        return {"refused": True}
    i = int(np.nanargmin(kf))
    kmin = float(kf[i])
    win = FINE[ok & (kf <= (1 + WINDOW) * kmin)]
    okc = np.isfinite(kc)
    order = np.argsort(np.where(okc, kc, np.inf))
    rank = [{"x": float(CAND[j]), "kappa": float(kc[j])} for j in order if okc[j]]
    refused = [float(CAND[j]) for j in range(len(CAND)) if not okc[j]]
    xs = float(FINE[i])
    edge = xs <= FINE[ok].min() + 1e-9 or xs >= FINE[ok].max() - 1e-9
    return {"argmin_x": xs, "kappa_min": kmin,
            "window": [float(win.min()), float(win.max())],
            "argmin_candidate": rank[0]["x"],
            "argmin_on_grid_edge": bool(edge),
            "inside_validated_domain": bool(in_domain(xs, T)) if domain_check else None,
            "window_inside_validated_domain": bool(in_domain(win.min(), T) and in_domain(win.max(), T)),
            "ranking": rank, "refused_or_unphysical_candidates": refused}


def summarize_boot(xs, ks):
    xs = np.array([v for v in xs if v is not None], float)
    ks = np.array([v for v in ks if v is not None], float)
    vals, cnt = np.unique(np.round(xs, 2), return_counts=True)
    top = sorted(zip(cnt, vals), reverse=True)[:5]
    return {"n_valid": int(len(xs)),
            "argmin_x_median": float(np.median(xs)),
            "argmin_x_p05_p95": [float(np.percentile(xs, 5)), float(np.percentile(xs, 95))],
            "kappa_min_median": float(np.median(ks)),
            "kappa_min_p05_p95": [float(np.percentile(ks, 5)), float(np.percentile(ks, 95))],
            "frac_argmin_x_ge_0.85": float(np.mean(xs >= 0.85)),
            "frac_argmin_x_le_0.10": float(np.mean(xs <= 0.10)),
            "frac_argmin_in_0.30_0.70": float(np.mean((xs >= 0.30) & (xs <= 0.70))),
            "top_argmin_x": [{"x": float(v), "frac": float(c) / len(xs)} for c, v in top]}


def boot_naive(rows, rng):
    res = {T: {"x": [], "k": [], "curves": []} for T in TEMPS}
    n = len(rows)
    for _ in range(N_BOOT):
        s = [rows[j] for j in rng.integers(0, n, n)]
        c = fit_naive(s)
        for T in TEMPS:
            kf = naive_kappa(c, FINE, T)
            res[T]["curves"].append(kf)
            if np.isfinite(kf).any():
                i = int(np.nanargmin(kf))
                res[T]["x"].append(float(FINE[i])); res[T]["k"].append(float(kf[i]))
            else:
                res[T]["x"].append(None); res[T]["k"].append(None)
    return res


def boot_scope(rng):
    rows = law["bulk_rows"]
    res = {T: {"x": [], "k": [], "curves": []} for T in TEMPS}
    sel_names = {}
    n = len(rows)
    for _ in range(N_BOOT):
        s = [dict(rows[j]) for j in rng.integers(0, n, n)]
        m = hgsr.fit(s, ["x", "T"])["selected"]
        key = "+".join(m["names"]); sel_names[key] = sel_names.get(key, 0) + 1
        terms = dict(zip(m["names"], m["coefs"]))
        for T in TEMPS:
            kf = scope_kappa(terms, FINE, T)
            res[T]["curves"].append(kf)
            if np.isfinite(kf).any():
                i = int(np.nanargmin(kf))
                res[T]["x"].append(float(FINE[i])); res[T]["k"].append(float(kf[i]))
            else:
                res[T]["x"].append(None); res[T]["k"].append(None)
    return res, sel_names


# ---------------------------------------------------------------- run -----
rows_a = lit_rows() + citrine_rows()
rows_a_noimpute = lit_rows(impute_T=False) + citrine_rows()
rows_b = lit_rows() + citrine_rows() + other_party_rows()
c_a, c_a2, c_b = fit_naive(rows_a), fit_naive(rows_a_noimpute), fit_naive(rows_b)

approaches = {
    "a_naive_lit_db": {"label": "(a) naive: literature as extracted + Citrine, one fit",
                       "n_rows": len(rows_a), "coef_inv_kappa": list(map(float, c_a)),
                       "fn": lambda T: (lambda x: naive_kappa(c_a, x, T))},
    "b_naive_pooled_all": {"label": "(b) naive: all parties pooled, one fit",
                           "n_rows": len(rows_b), "coef_inv_kappa": list(map(float, c_b)),
                           "fn": lambda T: (lambda x: naive_kappa(c_b, x, T))},
    "c_scope_aware": {"label": "(c) scope-aware: law shape x BTE calibration, refuses x > 0.90",
                      "n_rows": len(law["bulk_rows"]), "law_terms": LAW_TERMS,
                      "fn": lambda T: (lambda x: scope_kappa(LAW_TERMS, x, T))},
}
results = {"meta": {
    "task": "P1 screening-decision demo: SiGe composition window minimizing lattice kappa",
    "temperatures_K": list(TEMPS), "candidates_x": list(map(float, CAND)),
    "fine_grid_step": 0.005, "window_rule": "x with kappa <= 1.10 * kappa_min",
    "n_boot": N_BOOT, "seed": SEED,
    "inputs": [rel(KG_PATH), rel(os.path.join(PC, "final_law", "final_law.json")),
               rel(os.path.join(MT, "party5_databases", "party5_points.json")),
               rel(os.path.join(PC, "chd", "split_decision.json")),
               rel(os.path.join(PC, "ledger_campaign.jsonl")) + " (read only)"],
    "ledger_ops_used": {**SEQS, "scope-limit-alloy-law-x-le-0.90-2026-09-29": SEQ_CORNER},
    "naive_T_imputation": "literature rows without T are assigned 300 K in (a) and (b)",
    "fit_family_naive": "1/kappa = a + b x + c x^2 + d T (OLS, equal row weights)",
    "calibration": "r(x,T) = kappa_BTE/kappa_law at BTE nodes inside the domain, log-linear in x, flat beyond outermost node",
    "validity_domain": law["validity_domain"],
    "x_max_in_domain_by_T": {str(int(T)): float(max(x for x in FINE if in_domain(x, T))) for T in TEMPS},
    "bte_calibration_nodes": {str(int(T)): {str(x): {"kappa_BTE": BTE[(x, T)],
                                                     "kappa_law": float(law_kappa(LAW_TERMS, x, T)[0]),
                                                     "factor": BTE[(x, T)] / float(law_kappa(LAW_TERMS, x, T)[0])}
                                            for x in calib_nodes(T)} for T in TEMPS},
}, "approaches": {}}

for key, a in approaches.items():
    out = {k: v for k, v in a.items() if k != "fn"}
    out["decisions"] = {str(int(T)): decide(a["fn"](T), T) for T in TEMPS}
    results["approaches"][key] = out
# naive sensitivity: drop rows lacking T instead of imputing 300 K
results["approaches"]["a_naive_lit_db"]["sensitivity_no_T_imputation"] = {
    "n_rows": len(rows_a_noimpute), "coef_inv_kappa": list(map(float, c_a2)),
    "decisions": {str(int(T)): {k: v for k, v in decide(lambda x: naive_kappa(c_a2, x, T), T).items()
                               if k != "ranking"} for T in TEMPS}}
# scope-aware sensitivities: leave one BTE node out; one global factor per T
sens = {}
for T in TEMPS:
    for xn in calib_nodes(T):
        if len(calib_nodes(T, xn)) < 1:
            continue
        d = decide(lambda x: scope_kappa(LAW_TERMS, x, T, drop=xn), T)
        sens[f"T{int(T)}_drop_BTE_x{xn}"] = {k: d[k] for k in ("argmin_x", "kappa_min", "window")}
    med = float(np.median([BTE[(xn, T)] / float(law_kappa(LAW_TERMS, xn, T)[0]) for xn in calib_nodes(T)]))
    d = decide(lambda x: np.where([in_domain(v, T) for v in np.atleast_1d(x)],
                                  law_kappa(LAW_TERMS, x, T) * med, np.nan), T)
    sens[f"T{int(T)}_single_median_factor"] = {k: d[k] for k in ("argmin_x", "kappa_min", "window")}
results["approaches"]["c_scope_aware"]["sensitivity"] = sens

# bootstrap
rng = np.random.default_rng(SEED)
bA = boot_naive(rows_a, rng)
bB = boot_naive(rows_b, rng)
bC, selC = boot_scope(rng)
boots = {"a_naive_lit_db": bA, "b_naive_pooled_all": bB, "c_scope_aware": bC}
for key, b in boots.items():
    results["approaches"][key]["bootstrap"] = {str(int(T)): summarize_boot(b[T]["x"], b[T]["k"]) for T in TEMPS}
results["approaches"]["c_scope_aware"]["bootstrap_selected_law_forms"] = selC

# ----------------------------------------------------------- ablation -----
# Add the ledgered revisions one at a time (cumulative), starting from (a).
steps = []


def lit_db_fit(**kw):
    cap = kw.pop("x_cap", None)
    rows = lit_rows(x_cap=cap, **kw) + citrine_rows(x_cap=cap)
    c = fit_naive(rows)
    return rows, (lambda T, c=c, cap=cap: (lambda x: np.where(
        np.atleast_1d(x) <= (cap if cap else 9) + 1e-9, naive_kappa(c, x, T), np.nan)))


cfgs = [
    ("0 naive (a): literature as extracted + Citrine", {}),
    ("1 + scope-limit non-SiGe rows and forget absent values (seq %d, %d)"
     % (SEQS["scope-limit-literature-non-SiGe-2026-09-29"], SEQS["forget-literature-absent-values-2026-09-29"]),
     {"forget": True}),
    ("2 + correct row 34 x and quarantine unattributable rows (seq %d, %d)"
     % (SEQS["correct-literature-row34-x-2026-09-29"], SEQS["quarantine-literature-unattributable-2026-09-29"]),
     {"forget": True, "correct": True, "quarantine": True}),
    ("3 + sample-class scope split, keep literature-bulk (stage-0 split)",
     {"forget": True, "correct": True, "quarantine": True, "bulk_only": True}),
    ("4 + Ge-corner scope-limit x <= 0.90 (seq %s)" % SEQ_CORNER,
     {"forget": True, "correct": True, "quarantine": True, "bulk_only": True, "x_cap": 0.90}),
]
for name, kw in cfgs:
    rows, fnT = lit_db_fit(**dict(kw))
    steps.append({"step": name, "n_rows": len(rows),
                  "n_rows_strictly_inside_alloy_range_0.05_0.90": sum(1 for r in rows if 0.05 <= r["x"] <= 0.90),
                  "decisions": {str(int(T)): {k: v for k, v in decide(fnT(T), T).items() if k != "ranking"}
                                for T in TEMPS}})
# step 5: swap the literature fit for the MD-parented law shape (uncalibrated)
steps.append({"step": "5 replace the literature fit by the final-law shape (Tersoff MD, domain-refusing, no calibration)",
              "decisions": {str(int(T)): {k: v for k, v in decide(
                  lambda x, T=T: scope_kappa(LAW_TERMS, x, T, calibrate=False), T).items() if k != "ranking"}
                  for T in TEMPS}})
steps.append({"step": "6 + BTE-DFT per-regime calibration (= approach (c))",
              "decisions": {str(int(T)): {k: v for k, v in results["approaches"]["c_scope_aware"]["decisions"][str(int(T))].items()
                                          if k != "ranking"} for T in TEMPS}})
# leave-one-out from (c)
loo = {"c without domain refusal (law extrapolated to x = 0.95, calibration flat beyond last node)":
       {str(int(T)): {k: v for k, v in decide(lambda x, T=T: scope_kappa(LAW_TERMS, x, T, refuse=False), T).items()
                      if k != "ranking"} for T in TEMPS},
       "c without BTE calibration":
       {str(int(T)): {k: v for k, v in decide(lambda x, T=T: scope_kappa(LAW_TERMS, x, T, calibrate=False), T).items()
                      if k != "ranking"} for T in TEMPS}}
results["ablation_cumulative"] = steps
results["ablation_leave_one_out_from_c"] = loo

# ------------------------------------------------------------ checks ------
chk = []
for i in lit_rows(forget=True, correct=True, quarantine=True, bulk_only=True, impute_T=False):
    if 0.05 <= i["x"] <= 0.90:
        chk.append({"source": "literature-bulk (corrected)", "kg_index": i["kg"], "x": i["x"], "T": i["T"],
                    "kappa_obs": i["kappa"], "kappa_c": float(scope_kappa(LAW_TERMS, i["x"], i["T"])[0])
                    if i["T"] in TEMPS else None})
for r in citrine_rows():
    if 0.05 <= r["x"] <= 0.90:
        T = r["T"]
        # calibration nodes exist only at 300/700/1100 K; use nearest-T factor
        Tn = min(TEMPS, key=lambda t: abs(t - T))
        k = float(law_kappa(LAW_TERMS, r["x"], T)[0] * calib_factor(LAW_TERMS, r["x"], Tn)[0])
        chk.append({"source": "DB-CITRINE (experiment; mostly doped)", "x": r["x"], "T": T,
                    "kappa_obs": r["kappa"], "kappa_c_nearestT_factor": k})
results["checks_against_measurements"] = chk
results["experimental_reference"] = {
    "statement": "Abeles 1963 (Phys. Rev. 131, 1906) and Dismukes et al. 1964 (J. Appl. Phys. 35, 2899): "
                 "bulk Si1-xGex lattice kappa has a broad flat minimum over roughly x = 0.3-0.7, "
                 "about 5-9 W/mK at 300 K for undoped crystals; RTG legs use x = 0.2 partly for electrical, cost and density reasons.",
    "used_as": "external plausibility check only; not an input to any fit"}

json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=float)

# ------------------------------------------------------------- figure -----
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COL = {"a_naive_lit_db": "#eb6834", "b_naive_pooled_all": "#2a78d6", "c_scope_aware": "#1baf7a"}
LS = {"a_naive_lit_db": "--", "b_naive_pooled_all": ":", "c_scope_aware": "-"}
SHORT = {"a_naive_lit_db": "(a) naive: literature + Citrine",
         "b_naive_pooled_all": "(b) naive: all parties pooled",
         "c_scope_aware": "(c) scope-aware (law shape x BTE, refuses outside domain)"}
T = 1100.0
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.6, 1]})
ax = axes[0]
xdom = results["meta"]["x_max_in_domain_by_T"]["1100"]
ax.axvspan(X_MIN, xdom, color="#f0efec", zorder=0)
ax.text(0.06, 0.97, "validated domain at 1100 K\n(x 0.05 to %.2f; T <= 0.85 T_solidus)" % xdom,
        transform=ax.get_xaxis_transform(), va="top", fontsize=8, color="#52514e")
for key in ("a_naive_lit_db", "b_naive_pooled_all", "c_scope_aware"):
    cur = np.array(boots[key][T]["curves"])
    lo, hi = np.nanpercentile(cur, 5, axis=0), np.nanpercentile(cur, 95, axis=0)
    kf = approaches[key]["fn"](T)(FINE)
    ax.fill_between(FINE, lo, hi, color=COL[key], alpha=0.18, lw=0)
    ax.plot(FINE, kf, color=COL[key], ls=LS[key], lw=2, label=SHORT[key])
    d = results["approaches"][key]["decisions"]["1100"]
    ax.plot([d["argmin_x"]], [d["kappa_min"]], "o", ms=8, color=COL[key], mec="#fcfcfb", mew=2, zorder=5)
bx = [x for x in calib_nodes(T)]
ax.plot(bx, [BTE[(x, T)] for x in bx], "D", ms=7, color="#0b0b0b", mfc="#fcfcfb", mew=1.5,
        zorder=6, label="BTE-DFT calibration nodes (1100 K)")
ax.axvline(xdom, color="#52514e", lw=1)
ax.text(xdom + 0.01, 0.5, "(c) refuses\nhere", transform=ax.get_xaxis_transform(),
        fontsize=8, color="#52514e", va="center")
ax.set_xlim(0.05, 0.95)
ax.set_ylim(0, 16)
ax.set_xlabel("Ge fraction x in Si(1-x)Ge(x)")
ax.set_ylabel("lattice kappa at 1100 K (W/mK)")
ax.set_title("Screening call at 1100 K: kappa vs x (bands: 5-95% bootstrap)", fontsize=10, loc="left")
ax.legend(fontsize=8, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.86))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#e6e5e1", lw=0.8)
# right: bootstrap argmin distributions at 1100 K
ax = axes[1]
bins = np.arange(0.05, 0.9501, 0.025)
for key in ("a_naive_lit_db", "b_naive_pooled_all", "c_scope_aware"):
    xs = [v for v in boots[key][T]["x"] if v is not None]
    ax.hist(xs, bins=bins, histtype="step", lw=2, ls=LS[key], color=COL[key],
            weights=np.full(len(xs), 1.0 / N_BOOT), label=SHORT[key].split(" (law")[0])
ax.axvspan(X_MIN, xdom, color="#f0efec", zorder=0)
ax.set_xlim(0.05, 0.95)
ax.set_xlabel("argmin x (bootstrap, 500 reps)")
ax.set_ylim(0, 0.95)
ax.set_ylabel("fraction of resamples")
ax.set_title("Where each approach puts the minimum", fontsize=10, loc="left")
ax.legend(fontsize=8, frameon=False, loc="upper right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "fig_screening.png"), dpi=180, facecolor="#fcfcfb")

# ------------------------------------------------------------- console ----
for key, a in results["approaches"].items():
    print(key, "n =", a["n_rows"])
    for Ts, d in a["decisions"].items():
        b = a["bootstrap"][Ts]
        print(f"  T={Ts}: argmin x={d['argmin_x']:.3f} (cand {d['argmin_candidate']}) kmin={d['kappa_min']:.2f} "
              f"win={d['window']} inDomain={d['inside_validated_domain']} | boot x med {b['argmin_x_median']:.3f} "
              f"p5-95 {b['argmin_x_p05_p95']} kmin p5-95 {np.round(b['kappa_min_p05_p95'], 2).tolist()} n={b['n_valid']}")
for s in steps:
    d = s["decisions"]["1100"]
    print(s["step"], "| n", s.get("n_rows"), "| 1100K argmin", d.get("argmin_x"), "kmin",
          None if d.get("kappa_min") is None else round(d["kappa_min"], 2), "win", d.get("window"))
print("scope sens", json.dumps(sens))
print("boot law forms", selC)
