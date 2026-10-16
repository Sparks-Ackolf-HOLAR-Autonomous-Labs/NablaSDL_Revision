#!/usr/bin/env python3
"""P1 head-to-head (h2h_design.json, ledger seq 63): pooled symbolic regression
and multi-fidelity Gaussian process / Bayesian optimisation against the
shard-operation pipeline, on the evidence as first ingested (E0) and after the
ledgered operations (E1). Refuses to run if the design changed.
Oracle nodes are read from oracle/ (CHPC array 15922753); oracle metrics are
marked pending until all 14 are present.
Usage: ~/mat_theory_pilot/venv/bin/python head_to_head.py [--no-pysr]
"""
import glob, hashlib, json, os, random, sys, time
import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as Ck

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.dirname(HERE)
MT = os.path.dirname(PC)
reg = open(os.path.join(HERE, "PREREGISTERED_SHA256")).read().split()[0]
if hashlib.sha256(open(os.path.join(HERE, "h2h_design.json"), "rb").read()).hexdigest() != reg:
    sys.exit("h2h_design.json changed after registration")

# Reuse the screening demo's data layer and the pipeline's answer verbatim
# (everything above its decision section), without running its study.
src = open(os.path.join(PC, "screening_demo", "screening_demo.py")).read()
src = src.split("# ----------------------------------------------------------- decisions")[0]
G = {"__file__": os.path.join(PC, "screening_demo", "screening_demo.py"), "__name__": "sd"}
exec(compile(src, "screening_demo_head", "exec"), G)
kg, law = G["kg"], G["law"]
TEMPS = (300.0, 700.0, 1100.0)
CAND = np.round(np.arange(0.05, 0.951, 0.05), 2)
solidus = G["solidus"]


def row(q, party):
    return {"x": float(q["x_ge"]), "T": float(q["T_K"]), "kappa": float(q["kappa_W_mK"]), "party": party,
            "system": q.get("system")}


RAW_MACE = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(MT, "party4_mace", "raw", "mace_*.json")))]


def evidence(post):
    """E0 (post=False): as first ingested. E1: after the ledgered operations."""
    lit = G["lit_rows"](forget=post, correct=post, quarantine=post, bulk_only=post)
    for r in lit:
        r["fault"] = ("nonSiGe" if r["kg"] in G["NON_SIGE"] else None)
    rows = lit + [dict(r, fault=None) for r in G["citrine_rows"]()]
    ters = []
    for q in kg:
        if q.get("corpusId") in ("CHPC-MD", "DGX-MD"):
            r = row(q, "tersoff")
            r["fault"] = "ballistic" if r["x"] in (0.0, 1.0) else None
            if post and (r["x"] < 0.05 or r["x"] > 0.90 or r["system"] != "bulk" or r["T"] > 0.85 * solidus(r["x"])):
                continue
            ters.append(r)
    for b in law["bulk_rows"]:
        ters.append({"x": b["x"], "T": b["T"], "kappa": b["kappa"], "party": "tersoff", "fault": None})
    if post:
        mace = [row(q, "mace") for q in kg if q.get("corpusId") == "MACE-MD"]
        for r in mace:
            r["fault"] = None
    else:
        mace = [{"x": m["x"], "T": m["T"], "kappa": m["kappa_W_mK"], "party": "mace", "fault": "unitslip"} for m in RAW_MACE]
    bte = [dict(row(q, "bte"), fault=None) for q in kg if q.get("corpusId") == "BTE-DFT"]
    return {"exp": rows, "tersoff": ters, "mace": mace, "bte": bte}


EXP_BULK = [row(q, "exp_bulk") for q in kg if q.get("corpusId") == "DB-STARRY" and q.get("system") == "bulk"]


def load_oracle():
    o = {}
    for f in glob.glob(os.path.join(HERE, "oracle", "bte_x*_T*.json")):
        d = json.load(open(f))
        o[(round(d["x"], 3), float(d["T"]))] = d["kappa_W_mK"]
    return o


ORACLE = load_oracle()
ORACLE_DONE = len({x for x, _ in ORACLE}) == 14
BTE_ALL = dict(G["BTE"])
BTE_ALL.update(ORACLE)


# ---------------------------------------------------------------- models ----
def fit_pysr(rows):
    from pysr import PySRRegressor
    X = np.array([[r["x"], r["T"] / 1000] for r in rows])
    y = 1.0 / np.array([r["kappa"] for r in rows])
    m = PySRRegressor(niterations=60, populations=15, maxsize=22, binary_operators=["+", "-", "*", "/"],
                      unary_operators=[], model_selection="best", random_state=0, deterministic=True, procs=0,
                      multithreading=False, progress=False, verbosity=0, temp_equation_file=True,
                      delete_tempfiles=True)
    m.fit(X, y, variable_names=["x", "t"])

    def f(x, T):
        x = np.atleast_1d(np.asarray(x, float))
        r = m.predict(np.c_[x, np.full_like(x, T / 1000)])
        return np.where(r > 0, 1 / np.where(r > 0, r, 1), np.nan)
    return f, str(m.sympy())


def gp():
    return GaussianProcessRegressor(Ck(1.0) * RBF([0.3, 0.5], (1e-2, 1e2)) + WhiteKernel(1e-2, (1e-6, 1e1)),
                                    normalize_y=True, n_restarts_optimizer=3, random_state=0)


class MFGP:
    """Recursive linear autoregressive co-kriging on ln kappa:
    f_l(z) = rho_l * f_{l-1}(z) + delta_l(z), each level a GP (Le Gratiet 2013)."""

    def __init__(self, levels):
        self.levels, self.rho = [], []
        prev = None
        for rows in levels:
            Z = np.array([[r["x"], r["T"] / 1000] for r in rows])
            y = np.log([r["kappa"] for r in rows])
            if prev is None:
                rho, resid = 0.0, y
            else:
                mp = self._mean(Z, len(self.levels))
                A = np.c_[mp, np.ones_like(mp)]
                rho = float(np.linalg.lstsq(A, y, rcond=None)[0][0]) if len(y) > 2 else 1.0
                resid = y - rho * mp
            g = gp().fit(Z, resid)
            self.levels.append(g)
            self.rho.append(rho)
            prev = g
        self.train = levels

    def _mean(self, Z, upto):
        m = np.zeros(len(Z))
        for l in range(upto):
            m = self.rho[l] * m + self.levels[l].predict(Z)
        return m

    def predict(self, Z, level=None):
        L = len(self.levels) if level is None else level + 1
        m, v = np.zeros(len(Z)), np.zeros(len(Z))
        for l in range(L):
            mu, sd = self.levels[l].predict(Z, return_std=True)
            m = self.rho[l] * m + mu
            v = self.rho[l] ** 2 * v + sd ** 2
        return m, np.sqrt(v)

    def fn(self, level=None):
        def f(x, T):
            x = np.atleast_1d(np.asarray(x, float))
            return np.exp(self.predict(np.c_[x, np.full_like(x, T / 1000)], level)[0])
        return f

    def residuals(self):
        out = []
        for l, rows in enumerate(self.train):
            Z = np.array([[r["x"], r["T"] / 1000] for r in rows])
            m = self.predict(Z, l)[0]
            out += [(r, float(np.log(r["kappa"]) - mi)) for r, mi in zip(rows, m)]
        return out


def pipeline_fn(x, T):
    """Screening-demo approach (c). The BTE calibration exists at 300/700/1100 K;
    at other T its log factor is interpolated linearly in T (flat outside):
    deviation h2h-D1, needed to evaluate M1 on experimental rows at other T."""
    T = float(T)
    if T in TEMPS:
        return G["scope_kappa"](G["LAW_TERMS"], x, T)
    x = np.atleast_1d(np.asarray(x, float))
    lr = np.array([np.log(G["calib_factor"](G["LAW_TERMS"], x, Tn)) for Tn in TEMPS])
    r = np.exp([np.interp(T, TEMPS, lr[:, i]) for i in range(len(x))])
    k = G["law_kappa"](G["LAW_TERMS"], x, T) * r
    return np.where([G["in_domain"](xi, T) for xi in x], k, np.nan)


# --------------------------------------------------------------- metrics ----
def mape(pred, obs):
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    ok = np.isfinite(pred)
    return (float(np.median(np.abs(pred[ok] / obs[ok] - 1))) if ok.any() else None), int((~ok).sum())


def one(f, x, T):
    return float(np.atleast_1d(f(np.array([x]), T))[0])


def metrics(f, residuals=None):
    out = {}
    p = [one(f, r["x"], r["T"]) for r in EXP_BULK]
    out["M1_exp_bulk_MedAPE"], out["M1_refused"] = mape(p, [r["kappa"] for r in EXP_BULK])
    sub = [(pi, r) for pi, r in zip(p, EXP_BULK) if r["x"] <= 0.4]
    out["M1_exp_bulk_x_le_0.4_MedAPE"] = mape([a for a, _ in sub], [r["kappa"] for _, r in sub])[0]
    if ORACLE_DONE:
        ks = sorted(ORACLE)
        out["M2_bte_oracle_MedAPE"], out["M2_refused"] = mape([one(f, x, T) for x, T in ks], [ORACLE[k] for k in ks])
        k = f(CAND, 1100.0)
        out["M3_argmin_1100K"] = float(CAND[int(np.nanargmin(k))]) if np.isfinite(k).any() else None
        out["M3_error_x"] = abs(out["M3_argmin_1100K"] - TRUE_ARGMIN) if out["M3_argmin_1100K"] is not None else None
        out["M3_regret"] = BTE_ALL[(out["M3_argmin_1100K"], 1100.0)] / BTE_ALL[(TRUE_ARGMIN, 1100.0)] - 1
    else:
        out["M2_M3"] = "pending: BTE oracle array 15922753 not collected"
    out["M4_dkappa_300_to_1100"] = {str(x): one(f, x, 1100.0) - one(f, x, 300.0) for x in (0.2, 0.5)}
    out["M4_sign_correct"] = all(np.isfinite(v) and v < 0 for v in out["M4_dkappa_300_to_1100"].values())
    uns = 0
    for T in TEMPS:
        k = f(CAND, T)
        uns += sum(1 for x, ki in zip(CAND, k) if np.isfinite(ki) and (x > 0.90 + 1e-9 or T > 0.85 * solidus(x)))
    out["M5_unsupported_claims"] = uns
    out["kappa_1100K_on_CAND"] = [None if not np.isfinite(v) else float(v) for v in f(CAND, 1100.0)]
    if residuals is not None:
        res = np.array([e for _, e in residuals])
        cut = 3 * 1.4826 * np.median(np.abs(res - np.median(res)))
        fl = {}
        for fault in ("nonSiGe", "unitslip", "ballistic"):
            sel = [abs(e - np.median(res)) > cut for r, e in residuals if r.get("fault") == fault]
            fl[fault] = {"n_rows": len(sel), "n_flagged": int(sum(sel)), "flagged": bool(len(sel) > 0 and sum(sel) >= len(sel) / 2)}
        out["M6_fault_flags"] = fl
    return out


def sr_residuals(f, rows):
    return [(r, float(np.log(r["kappa"]) - np.log(one(f, r["x"], r["T"])))) for r in rows
            if np.isfinite(one(f, r["x"], r["T"])) and one(f, r["x"], r["T"]) > 0]


# ---------------------------------------------------------------- replay ----
def replay(mace_rows, E, known_x, rng=None, max_q=10):
    """MF-BO on the BTE level at 1100 K over CAND; oracle answers queries."""
    known = [dict(x=x, T=T, kappa=v, party="bte") for (x, T), v in BTE_ALL.items() if x in known_x]
    queried, trace = [], []
    for step in range(max_q + 1):
        mf = MFGP([E["tersoff"], mace_rows, known])
        mu, sd = mf.predict(np.c_[CAND, np.full(len(CAND), 1.1)])
        pick = float(CAND[int(np.argmin(mu))])
        trace.append({"queries": len(queried), "decision": pick, "err_x": round(abs(pick - TRUE_ARGMIN), 3),
                      "regret": BTE_ALL[(pick, 1100.0)] / BTE_ALL[(TRUE_ARGMIN, 1100.0)] - 1})
        best = min(np.log(r["kappa"]) for r in known if r["T"] == 1100.0)
        avail = [i for i, x in enumerate(CAND) if x not in known_x and x not in queried]
        if not avail or step == max_q:
            break
        if rng is None:
            z = (best - mu) / np.maximum(sd, 1e-9)
            ei = (best - mu) * norm.cdf(z) + sd * norm.pdf(z)
            i = max(avail, key=lambda j: ei[j])
            if ei[i] < 0.01 * abs(best):
                trace[-1]["stop"] = "EI below 1% of best"
                break
        else:
            i = rng.choice(avail)
        x = float(CAND[i])
        queried.append(x)
        for T in TEMPS:
            if (x, T) in BTE_ALL:
                known.append(dict(x=x, T=T, kappa=BTE_ALL[(x, T)], party="bte"))
    return {"queried": queried, "trace": trace}


def main():
    global TRUE_ARGMIN
    t0 = time.time()
    res = {"design_sha256": reg, "ledger_prereg_seq": 63, "oracle_complete": ORACLE_DONE,
           "n_exp_bulk": len(EXP_BULK)}
    if ORACLE_DONE:
        k1100 = {x: BTE_ALL[(x, 1100.0)] for x in CAND}
        TRUE_ARGMIN = min(k1100, key=k1100.get)
        res["truth"] = {"argmin_1100K": TRUE_ARGMIN, "kappa_1100K_grid": {str(x): v for x, v in k1100.items()}}
    E0, E1 = evidence(False), evidence(True)
    res["evidence_sizes"] = {k: {p: len(v) for p, v in E.items()} for k, E in (("E0", E0), ("E1", E1))}
    M = {}
    M["D_pipeline"] = metrics(pipeline_fn)
    M["D_pipeline"]["M6_fault_flags"] = {"nonSiGe": "flagged (ledger seq 20, second extractor)",
                                         "unitslip": "flagged (ledger seq 1, cross-party bound)",
                                         "ballistic": "flagged (ledger seq 0 scope-limit to alloys)"}
    for tag, E in (("E0", E0), ("E1", E1)):
        mf = MFGP([E["tersoff"], E["mace"], E["bte"]])
        M[f"C_MFGP_{tag}"] = metrics(mf.fn(), mf.residuals())
        M[f"C_MFGP_{tag}"]["rho"] = mf.rho
        mf2 = MFGP([E["tersoff"], E["mace"], E["bte"], E["exp"]])
        M[f"C2_MFGP_exp_target_{tag}"] = metrics(mf2.fn(), mf2.residuals())
        M[f"C2_MFGP_exp_target_{tag}"]["rho"] = mf2.rho
        if "--no-pysr" not in sys.argv:
            pooled = E["exp"] + E["tersoff"] + E["mace"] + E["bte"]
            f, eq = fit_pysr(pooled)
            M[f"A_pooledSR_{tag}"] = metrics(f, sr_residuals(f, pooled))
            M[f"A_pooledSR_{tag}"]["equation_1_over_kappa"] = eq
            M[f"A_pooledSR_{tag}"]["n_rows"] = len(pooled)
    if "--no-pysr" not in sys.argv:
        f, eq = fit_pysr(E0["bte"])
        M["A2_SR_BTE_only"] = metrics(f)
        M["A2_SR_BTE_only"]["equation_1_over_kappa"] = eq
    res["methods"] = M
    if ORACLE_DONE:
        start = {0.0, 0.15, 0.2, 0.5, 0.85, 1.0}
        R = {"MF_BO": replay(E0["mace"], E0, start), "MF_BO_clean": replay(E1["mace"], E1, start)}
        rr = [replay(E0["mace"], E0, start, rng=random.Random(s), max_q=10)["trace"] for s in range(200)]
        R["random_median_err_x_by_queries"] = [float(np.median([t[q]["err_x"] for t in rr if len(t) > q]))
                                               for q in range(11)]
        R["random_queries_to_within_0.05"] = float(np.median([next((t_["queries"] for t_ in t if t_["err_x"] <= 0.05 + 1e-9), 99) for t in rr]))
        pk = round(0.505 / 0.05) * 0.05
        R["pipeline"] = {"queries": 1, "queried": [0.7], "decision_continuous": 0.505, "decision_grid": round(pk, 2),
                         "err_x": abs(round(pk, 2) - TRUE_ARGMIN),
                         "regret": BTE_ALL[(round(pk, 2), 1100.0)] / BTE_ALL[(TRUE_ARGMIN, 1100.0)] - 1}
        R["cost_per_BTE_point_cpu_min"] = 28
        res["replay"] = R
    res["wall_s"] = time.time() - t0
    json.dump(res, open(os.path.join(HERE, "h2h_results.json"), "w"), indent=1, default=float)
    print(json.dumps({k: {m: v for m, v in d.items() if m.startswith("M") and m != "M6_fault_flags"} for k, d in M.items()}, indent=1, default=float))


TRUE_ARGMIN = None
if __name__ == "__main__":
    main()
