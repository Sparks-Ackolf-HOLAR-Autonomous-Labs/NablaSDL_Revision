"""Blind fault injector for the P2 production fault study (Si(1-x)Ge(x), Tersoff RNEMD).

Written blind (no access to any detector code or detector result) by the
blind catalog subagent, 2026-09-28. The human-readable catalog is
FAULT_CATALOG.md; the machine-readable one is fault_catalog.json. This module
implements every catalog entry plus the NULL campaign.

Public API
----------
entries() -> list[str]
inject(rows, entry_id, trial_seed, other_parties=None) -> (rows_out, truth)

Contract
--------
* rows follow the production schema
  {run_id, batch_id, party, x, T, ncz, seed, kappa, n_atoms}. Output rows have
  exactly the same keys and value types; ground truth lives ONLY in `truth`.
* Deterministic given trial_seed: rng = numpy.random.default_rng(trial_seed).
* Every trial (NULL included) applies the same background: a replica-level
  multiplicative jitter exp(N(0, BACKGROUND_SIGMA)) on kappa and a random row
  order. The fault is applied on top, so fault and NULL trials differ only by
  the fault.
* Output numbers are rounded to the decimal precision seen in the input so
  that edited values do not stand out by their number of digits.
* other_parties (rows in the evidence_table.json format) are accepted for
  context but never modified; the injector does not need them.

Pure python + numpy.
"""
from __future__ import annotations

import copy
import re
from typing import Callable

import numpy as np

BACKGROUND_SIGMA = 0.01          # relative replica jitter applied in every trial
H_CUT = 0.85                     # homologous temperature T/T_sol above which real SiGe is premelting
KEYS = ("run_id", "batch_id", "party", "x", "T", "ncz", "seed", "kappa", "n_atoms")

# Approximate real Si-Ge solidus (K) vs Ge fraction, from the assessed Si-Ge
# phase diagram (lens-shaped, Ge 1211 K, Si 1687 K). Accuracy about +/-30 K; the
# catalog only needs the homologous temperature to that precision.
_SOL_X = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
_SOL_T = np.array([1687, 1640, 1590, 1535, 1480, 1425, 1370, 1320, 1275, 1240, 1211.0])


def t_solidus(x: float) -> float:
    return float(np.interp(x, _SOL_X, _SOL_T))


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _decimals(vals) -> int:
    d = 0
    for v in vals:
        if isinstance(v, float):
            s = repr(v)
            if "e" in s or "E" in s:
                return 6
            if "." in s:
                d = max(d, len(s.split(".")[1].rstrip("0")))
    return min(d, 8)


class _Fmt:
    """Records the input number formats so edited values look like originals."""

    def __init__(self, rows):
        self.dec = {k: _decimals([r[k] for r in rows]) for k in ("x", "T", "kappa")}
        self.types = {k: type(rows[0][k]) for k in KEYS}

    def num(self, key, v):
        t = self.types[key]
        if t is int:
            return int(round(v))
        return round(float(v), max(self.dec.get(key, 6), 3 if key == "kappa" else 0))


def _point_key(r):
    return (r["batch_id"], r["x"], r["T"])


def _points(rows):
    pts = {}
    for i, r in enumerate(rows):
        pts.setdefault(_point_key(r), []).append(i)
    return pts


def _batches(rows):
    out = []
    for r in rows:
        if r["batch_id"] not in out:
            out.append(r["batch_id"])
    return sorted(out)


def _next_batch_id(rows, k=1):
    ids = _batches(rows)
    nums = []
    pref = None
    for b in ids:
        m = re.match(r"^(.*?)(\d+)$", str(b))
        if m:
            pref = m.group(1)
            nums.append(int(m.group(2)))
    if pref is None:
        return f"{ids[0]}_{k}"
    return f"{pref}{max(nums) + k}"


def _new_run_id(template: dict, new_batch: str, new_seed, existing: set, x=None, T=None, ncz=None):
    """Derive a run_id in the same textual style as a template row."""
    rid = str(template["run_id"])
    rid = rid.replace(str(template["batch_id"]), str(new_batch))
    if str(template["seed"]) in rid:
        rid = rid.replace(str(template["seed"]), str(new_seed))
    if x is not None and str(template["x"]) in rid:
        rid = rid.replace(str(template["x"]), str(x))
    if T is not None and str(template["T"]) in rid:
        rid = rid.replace(str(template["T"]), str(T))
    base, k = rid, 2
    while rid in existing:
        rid = f"{base}-r{k}"
        k += 1
    existing.add(rid)
    return rid


def _kappa_ref(rows, idxs):
    """kappa of the largest box in a point (reference for size-consistent physics edits)."""
    j = max(idxs, key=lambda i: rows[i]["ncz"])
    return float(rows[j]["kappa"])


def _fit_inverse_model(rows) -> Callable[[float, float, float], float]:
    """Smooth least-squares model of 1/kappa(x, T, ncz) used to synthesize new
    crystalline-Tersoff rows. 1/kappa is close to linear in 1/L."""
    def feats(x, T, n):
        t = T / 1000.0
        u = 1.0 / n
        return [1, x, x * x, x ** 3, t, t * t, x * t, u, x * u, x * x * u, t * u]
    A = np.array([feats(r["x"], r["T"], r["ncz"]) for r in rows], float)
    y = np.array([1.0 / r["kappa"] for r in rows], float)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)

    def pred(x, T, n):
        v = float(np.dot(feats(x, T, n), coef))
        return 1.0 / max(v, 1e-3)
    return pred


def _natoms_for(rows, ncz):
    for r in rows:
        if r["ncz"] == ncz:
            return r["n_atoms"]
    r = rows[0]
    return type(r["n_atoms"])(round(r["n_atoms"] * ncz / r["ncz"]))


def _background_method_off(rows):
    return sorted(r["run_id"] for r in rows if r["T"] / t_solidus(r["x"]) >= H_CUT)


def _truth(entry_id, category, **kw):
    t = dict(entry_id=entry_id, category=category, affected_run_ids=[], added_run_ids=[],
             affected_batches=[], regime=None, severity_u=None, magnitude={},
             expected_operator=None, acceptable_operators=[], forbidden_operators=[])
    t.update(kw)
    return t


def _pick_batch(rows, rng):
    b = _batches(rows)
    return b[int(rng.integers(len(b)))]


# --------------------------------------------------------------------------
# planted errors
# --------------------------------------------------------------------------

def _p01_biased_batch(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    d = 0.03 + u * (0.80 - 0.03)            # relative bias 3% .. 80%
    up = bool(rng.uniform() < 0.5)
    f = 1.0 + d if up else 1.0 / (1.0 + d)
    b = _pick_batch(rows, rng)
    aff = []
    for r in rows:
        if r["batch_id"] == b:
            r["kappa"] = fmt.num("kappa", r["kappa"] * f)
            aff.append(r["run_id"])
    return _truth("P01", "planted-error", affected_run_ids=aff, affected_batches=[b],
                  severity_u=u, magnitude=dict(factor=f, relative_bias=d, direction="up" if up else "down"),
                  expected_operator="quarantine", acceptable_operators=["quarantine", "correct", "downweight", "forget"],
                  forbidden_operators=["retain", "strengthen"])


_UNIT_SLIPS = [  # ordered from subtle to gross
    (2.0, "Muller-Plathe periodic flux: missing factor 1/2 (heat flows both ways through the box)"),
    (0.5, "Muller-Plathe periodic flux: factor 1/2 applied twice"),
    (0.01, "reported in W/(cm K) instead of W/(m K)"),
    (100.0, "cross-section area in nm^2 used where Angstrom^2 expected"),
    (1000.0, "reported in mW/(m K)"),
]


def _p02_unit_slip(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    k = min(int(u * len(_UNIT_SLIPS)), len(_UNIT_SLIPS) - 1)
    f, why = _UNIT_SLIPS[k]
    b = _pick_batch(rows, rng)
    aff = []
    for r in rows:
        if r["batch_id"] == b:
            r["kappa"] = fmt.num("kappa", r["kappa"] * f)
            aff.append(r["run_id"])
    return _truth("P02", "planted-error", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  magnitude=dict(factor=f, slip=why), expected_operator="correct",
                  acceptable_operators=["correct", "quarantine", "forget"],
                  forbidden_operators=["retain", "strengthen", "scope-limit"])


def _p03_x_swap(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    target = 0.05 + u * (0.60 - 0.05)       # target |dx|
    pts = _points(rows)
    keys = list(pts)
    pairs = [(a, c) for i, a in enumerate(keys) for c in keys[i + 1:] if a[0] == c[0]]
    if not pairs:
        pairs = [(a, c) for i, a in enumerate(keys) for c in keys[i + 1:]]
    dxs = np.array([abs(a[1] - c[1]) for a, c in pairs])
    order = np.argsort(np.abs(dxs - target))
    j = int(order[int(rng.integers(min(3, len(order))))])
    a, c = pairs[j]
    xa, xc = a[1], c[1]
    aff = []
    for i in pts[a]:
        rows[i]["x"] = xc
        aff.append(rows[i]["run_id"])
    for i in pts[c]:
        rows[i]["x"] = xa
        aff.append(rows[i]["run_id"])
    return _truth("P03", "planted-error", affected_run_ids=aff, affected_batches=sorted({a[0], c[0]}),
                  severity_u=u, magnitude=dict(dx=abs(xa - xc), x_a=xa, x_b=xc, T_a=a[2], T_b=c[2]),
                  expected_operator="correct", acceptable_operators=["correct", "quarantine", "forget"],
                  forbidden_operators=["retain", "strengthen"])


def _p04_species_swap(rows, rng, fmt, ctx):
    """LAMMPS atom-type map reversed in one batch's data-file template: label x
    is really 1-x. Severity: fraction of the batch and distance from x=0.5."""
    u = float(rng.uniform())
    b = _pick_batch(rows, rng)
    pts = [k for k in _points(rows) if k[0] == b]
    pts.sort(key=lambda k: abs(k[1] - 0.5))          # closest to 0.5 first (subtle)
    n = max(1, int(round(1 + u * (len(pts) - 1))))
    chosen = pts[len(pts) - n:] if u > 0.5 else pts[:n]
    idx = _points(rows)
    aff = []
    for k in chosen:
        for i in idx[k]:
            rows[i]["x"] = fmt.num("x", 1.0 - rows[i]["x"])
            aff.append(rows[i]["run_id"])
    return _truth("P04", "planted-error", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  magnitude=dict(n_points=n, n_points_batch=len(pts),
                                 mean_abs_2x_minus_1=float(np.mean([abs(2 * k[1] - 1) for k in chosen]))),
                  expected_operator="correct", acceptable_operators=["correct", "quarantine", "forget"],
                  forbidden_operators=["retain", "strengthen"])


def _p05_T_offset(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    celsius = u > 0.9
    if celsius:
        dT = -273.15
        slip = "labels written in degrees Celsius"
    else:
        dT = (20.0 + (u / 0.9) * (300.0 - 20.0)) * (1 if rng.uniform() < 0.5 else -1)
        slip = "thermostat set-point vs measured slab temperature / copied input deck"
    b = _pick_batch(rows, rng)
    aff = []
    for r in rows:
        if r["batch_id"] == b:
            r["T"] = fmt.num("T", r["T"] + dT)
            aff.append(r["run_id"])
    return _truth("P05", "planted-error", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  magnitude=dict(dT=dT, slip=slip), expected_operator="correct",
                  acceptable_operators=["correct", "quarantine", "downweight"],
                  forbidden_operators=["retain", "strengthen"])


def _p06_duplicate(rows, rng, fmt, ctx):
    """Double ingestion of a batch. u<1/3: re-run under a new batch id with the
    same seeds and small hardware non-determinism; 1/3..2/3: new ids, bitwise
    identical kappa; >2/3: identical run_ids replayed."""
    u = float(rng.uniform())
    b = _pick_batch(rows, rng)
    src = [r for r in rows if r["batch_id"] == b]
    frac = 0.5 + 0.5 * float(rng.uniform())
    n = max(1, int(round(frac * len(src))))
    pick = sorted(rng.choice(len(src), size=n, replace=False).tolist())
    existing = {r["run_id"] for r in rows}
    nb = _next_batch_id(rows)
    added = []
    if u < 1 / 3:
        mode, noise = "resubmitted-new-ids-hw-jitter", 1e-4 + (u * 3) * (5e-3 - 1e-4)
    elif u < 2 / 3:
        mode, noise = "resubmitted-new-ids-identical-kappa", 0.0
    else:
        mode, noise = "replayed-identical-rows", 0.0
    for j in pick:
        r = copy.deepcopy(src[j])
        if mode != "replayed-identical-rows":
            r["batch_id"] = nb
            r["run_id"] = _new_run_id(src[j], nb, r["seed"], existing)
            if noise:
                r["kappa"] = fmt.num("kappa", r["kappa"] * float(np.exp(rng.normal(0, noise))))
        rows.append(r)
        added.append(r["run_id"])
    return _truth("P06", "planted-error", affected_run_ids=[src[j]["run_id"] for j in pick],
                  added_run_ids=added, affected_batches=[b] + ([nb] if mode != "replayed-identical-rows" else []),
                  severity_u=u, magnitude=dict(mode=mode, hw_noise=noise, n_duplicated=n, duplicate_batch=nb),
                  expected_operator="forget",
                  acceptable_operators=["forget", "downweight"],
                  forbidden_operators=["strengthen"],
                  note="forget applies to the duplicate copies only; the originals should be retained")


def _p07_unequilibrated_long_box(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    d = 0.03 + u * (0.40 - 0.03)
    b = _pick_batch(rows, rng)
    nmax = max(r["ncz"] for r in rows)
    aff = []
    for r in rows:
        if r["batch_id"] == b and r["ncz"] == nmax:
            # longer relaxation of the long box: not yet at steady state
            r["kappa"] = fmt.num("kappa", r["kappa"] * (1.0 - d * float(rng.uniform(0.7, 1.0))))
            aff.append(r["run_id"])
    return _truth("P07", "planted-error", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  magnitude=dict(max_relative_deficit=d, ncz=nmax), expected_operator="forget",
                  acceptable_operators=["forget", "quarantine", "downweight"],
                  forbidden_operators=["retain", "strengthen"])


def _p08_party_mislabel(rows, rng, fmt, ctx):
    """MACE-MD rows ingested under the CHPC-MD-C party label."""
    u = float(rng.uniform())
    b = _pick_batch(rows, rng)
    pts = [k for k in _points(rows) if k[0] == b]
    n = max(1, int(round(1 + u * (len(pts) - 1))))
    chosen = [pts[i] for i in sorted(rng.choice(len(pts), size=n, replace=False).tolist())]
    r0 = float(rng.uniform(0.50, 0.60))
    idx = _points(rows)
    aff = []
    for k in chosen:
        rx = r0 * (1.0 + 0.15 * (k[1] - 0.5)) * float(np.exp(rng.normal(0, 0.03)))
        for i in idx[k]:
            rows[i]["kappa"] = fmt.num("kappa", rows[i]["kappa"] * rx)
            aff.append(rows[i]["run_id"])
    return _truth("P08", "planted-error", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  magnitude=dict(n_points=n, n_points_batch=len(pts), mace_over_tersoff=r0),
                  expected_operator="correct",
                  acceptable_operators=["correct", "split", "quarantine", "replace"],
                  forbidden_operators=["retain", "strengthen"],
                  note="correct = re-attribute to the MACE-MD party (data are valid MACE output)")


# --------------------------------------------------------------------------
# method-off data
# --------------------------------------------------------------------------

def _add_batch(rows, fmt, rng, pts_xT, kappa_fn, label_noise=True):
    """Append a new batch of points (each at every box size). Returns run_ids."""
    nb = _next_batch_id(rows)
    sizes = sorted({r["ncz"] for r in rows})
    existing = {r["run_id"] for r in rows}
    seed0 = max(int(r["seed"]) for r in rows) + 1
    tmpl_by_n = {}
    for r in rows:
        tmpl_by_n.setdefault(r["ncz"], r)
    added = []
    for p, (x, T) in enumerate(pts_xT):
        seed = seed0 + p
        xs, Ts = fmt.num("x", x), fmt.num("T", T)
        for n in sizes:
            t = tmpl_by_n[n]
            k = kappa_fn(x, T, n) * float(np.exp(rng.normal(0, BACKGROUND_SIGMA)))
            r = dict(t)
            r.update(batch_id=nb, x=xs, T=Ts, ncz=n, seed=type(t["seed"])(seed),
                     kappa=fmt.num("kappa", k), n_atoms=_natoms_for(rows, n))
            r["run_id"] = _new_run_id(t, nb, seed, existing, x=xs, T=Ts)
            rows.append(r)
            added.append(r["run_id"])
    return nb, added


def _m01_near_solidus(rows, rng, fmt, ctx):
    """New batch in the premelting band of the REAL alloy (T/T_sol >= H_CUT).
    Tersoff stays crystalline, so kappa follows the smooth crystalline trend."""
    u = float(rng.uniform())
    model = _fit_inverse_model(rows)
    npts = 3 + int(round(5 * u))
    hs, pts = [], []
    for _ in range(npts):
        h = float(rng.uniform(0.86, 0.86 + 0.115 * (0.3 + 0.7 * u)))
        xs = np.linspace(0.05, 0.95, 181)
        ok = xs[np.array([h * t_solidus(v) <= 1200 for v in xs])]
        x = float(rng.uniform(ok.min(), 0.95)) if len(ok) else 0.95
        T = min(h * t_solidus(x), 1200.0)
        hs.append(T / t_solidus(x))
        pts.append((x, T))
    nb, added = _add_batch(rows, fmt, rng, pts, model)
    return _truth("M01", "method-off-data", added_run_ids=added, affected_run_ids=added, affected_batches=[nb],
                  regime=f"T/T_solidus(x) >= {H_CUT} (real Si-Ge solidus)", severity_u=u,
                  magnitude=dict(n_points=npts, homologous_T=hs), expected_operator="scope-limit",
                  acceptable_operators=["scope-limit", "split", "downweight"],
                  forbidden_operators=["correct", "strengthen"],
                  note="also scope-limit every pre-existing row listed in background_method_off_run_ids")


def _m02_amorphous(rows, rng, fmt, ctx):
    """Some points of one batch are amorphous (melt-quench slip in structure
    generation): kappa is size independent and weakly increasing with T."""
    u = float(rng.uniform())
    b = _pick_batch(rows, rng)
    pts = [k for k in _points(rows) if k[0] == b]
    n = max(1, int(round(1 + u * (len(pts) - 1))))
    chosen = [pts[i] for i in sorted(rng.choice(len(pts), size=n, replace=False).tolist())]
    idx = _points(rows)
    lev = []
    aff = []
    for k in chosen:
        ii = idx[k]
        ks = sorted(float(rows[i]["kappa"]) for i in ii)
        kmid = ks[len(ks) // 2]
        # subtle: level near the mid-size crystalline value; gross: far from it
        level = 1.0 + (1 if rng.uniform() < 0.5 else -1) * u * 0.5
        level *= 1.0 + 0.08 * (k[2] - 300.0) / 900.0
        lev.append(level)
        ka = kmid * level
        for i in ii:
            rows[i]["kappa"] = fmt.num("kappa", ka * float(np.exp(rng.normal(0, BACKGROUND_SIGMA))))
            aff.append(rows[i]["run_id"])
    return _truth("M02", "method-off-data", affected_run_ids=aff, affected_batches=[b], severity_u=u,
                  regime="amorphous Si-Ge (not the crystalline alloy the law describes)",
                  magnitude=dict(n_points=n, n_points_batch=len(pts), level_over_mid_size=lev),
                  expected_operator="split", acceptable_operators=["split", "quarantine", "scope-limit"],
                  forbidden_operators=["retain", "strengthen", "correct"])


def _m03_dilute_ballistic(rows, rng, fmt, ctx):
    """Dilute-alloy, low-T points where phonon mean free paths exceed the
    longest box: 1/kappa is concave in 1/L and the 3-size extrapolation fails."""
    u = float(rng.uniform())
    xc = 0.10 + 0.15 * u
    Tc = 500.0 + 400.0 * u
    a = 0.10 + 0.9 * u
    sizes = sorted({r["ncz"] for r in rows})
    nmin, nmax = sizes[0], sizes[-1]
    pts = _points(rows)
    aff = []
    for k, ii in pts.items():
        _, x, T = k
        w = max(0.0, 1.0 - min(x, 1 - x) / xc) * max(0.0, 1.0 - (T - 300.0) / (Tc - 300.0 + 1e-9))
        if w <= 0:
            continue
        for i in ii:
            s = (rows[i]["ncz"] - nmin) / max(nmax - nmin, 1)
            rows[i]["kappa"] = fmt.num("kappa", rows[i]["kappa"] * (1.0 + a * w * s * s))
            aff.append(rows[i]["run_id"])
    if not aff:  # guarantee a non-empty regime: widen to the most dilute point
        k = min(pts, key=lambda q: (min(q[1], 1 - q[1]), q[2]))
        for i in pts[k]:
            s = (rows[i]["ncz"] - nmin) / max(nmax - nmin, 1)
            rows[i]["kappa"] = fmt.num("kappa", rows[i]["kappa"] * (1.0 + a * s * s))
            aff.append(rows[i]["run_id"])
    return _truth("M03", "method-off-data", affected_run_ids=aff,
                  affected_batches=sorted({r["batch_id"] for r in rows if r["run_id"] in set(aff)}),
                  regime=f"min(x,1-x) < {xc:.3f} and T < {Tc:.0f} K (MFP >> box)", severity_u=u,
                  magnitude=dict(x_c=xc, T_c=Tc, max_long_box_enhancement=a),
                  expected_operator="scope-limit", acceptable_operators=["scope-limit", "split", "downweight"],
                  forbidden_operators=["forget", "correct"])


# --------------------------------------------------------------------------
# valid anomalies (must NOT be forgotten)
# --------------------------------------------------------------------------

def _add_resistance(rows, fn, fmt):
    """1/kappa_row += fn(x,T) / kappa_ref(point): intrinsic extra scattering that
    leaves the 1/L slope unchanged (physics, not a batch artefact)."""
    aff = []
    for k, ii in _points(rows).items():
        g = fn(k[1], k[2])
        if abs(g) < 1e-6:
            continue
        kref = _kappa_ref(rows, ii)
        for i in ii:
            rows[i]["kappa"] = fmt.num("kappa", 1.0 / (1.0 / rows[i]["kappa"] + g / kref))
            if abs(g) >= 0.01:   # listed as affected only above 1% extra resistance
                aff.append(rows[i]["run_id"])
    return aff


def _v01_local_dip(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    A = 0.03 + u * (0.35 - 0.03)
    x0 = float(rng.uniform(0.3, 0.7))
    T0 = float(rng.uniform(300, 800))
    sx = float(rng.uniform(0.08, 0.15))
    sT = float(rng.uniform(100, 250))
    fn = lambda x, T: A * np.exp(-0.5 * ((x - x0) / sx) ** 2 - 0.5 * ((T - T0) / sT) ** 2)
    aff = _add_resistance(rows, fn, fmt)
    return _truth("V01", "valid-anomaly", affected_run_ids=aff,
                  affected_batches=sorted({r["batch_id"] for r in rows if r["run_id"] in set(aff)}),
                  regime=f"Gaussian bump centred x={x0:.2f}, T={T0:.0f} K (sx={sx:.2f}, sT={sT:.0f} K)",
                  severity_u=u, magnitude=dict(A_relative_resistance=A, x0=x0, T0=T0, sx=sx, sT=sT),
                  expected_operator="retain", acceptable_operators=["retain", "strengthen", "split", "scope-limit"],
                  forbidden_operators=["forget", "quarantine", "correct", "replace"])


def _v02_high_T_channel(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    c = 0.05 + u * (0.50 - 0.05)
    Ton = float(rng.uniform(600, 900))
    fn = lambda x, T: c * (max(T - Ton, 0.0) / (1200.0 - Ton)) ** 2
    aff = _add_resistance(rows, fn, fmt)
    return _truth("V02", "valid-anomaly", affected_run_ids=aff,
                  affected_batches=sorted({r["batch_id"] for r in rows if r["run_id"] in set(aff)}),
                  regime=f"T > {Ton:.0f} K, extra resistance growing as (T-T_on)^2",
                  severity_u=u, magnitude=dict(c_relative_resistance_at_1200K=c, T_on=Ton),
                  expected_operator="retain", acceptable_operators=["retain", "strengthen", "split", "scope-limit"],
                  forbidden_operators=["forget", "quarantine", "correct", "replace"])


def _v03_asymmetry(rows, rng, fmt, ctx):
    u = float(rng.uniform())
    a = 0.03 + u * (0.30 - 0.03)
    fn = lambda x, T: a * (2.0 * x - 1.0)
    aff = _add_resistance(rows, fn, fmt)
    return _truth("V03", "valid-anomaly", affected_run_ids=aff,
                  affected_batches=_batches(rows), regime="global, antisymmetric about x=0.5 (Ge side lower)",
                  severity_u=u, magnitude=dict(a_relative_resistance=a),
                  expected_operator="retain", acceptable_operators=["retain", "strengthen", "split"],
                  forbidden_operators=["forget", "quarantine", "correct", "replace", "scope-limit"])


def _null(rows, rng, fmt, ctx):
    return _truth("NULL", "null", expected_operator="retain", acceptable_operators=["retain", "strengthen"],
                  forbidden_operators=["forget", "quarantine", "correct", "replace"], severity_u=None)


_REGISTRY = {
    "NULL": (0, _null),
    "P01": (1, _p01_biased_batch),
    "P02": (2, _p02_unit_slip),
    "P03": (3, _p03_x_swap),
    "P04": (4, _p04_species_swap),
    "P05": (5, _p05_T_offset),
    "P06": (6, _p06_duplicate),
    "P07": (7, _p07_unequilibrated_long_box),
    "P08": (8, _p08_party_mislabel),
    "M01": (9, _m01_near_solidus),
    "M02": (10, _m02_amorphous),
    "M03": (11, _m03_dilute_ballistic),
    "V01": (12, _v01_local_dip),
    "V02": (13, _v02_high_T_channel),
    "V03": (14, _v03_asymmetry),
}


def entries() -> list[str]:
    """Fault entry ids (NULL excluded)."""
    return [k for k in _REGISTRY if k != "NULL"]


def trial_seeds(entry_id: str, n_trials: int = 50) -> list[int]:
    """Pre-registered trial seeds: 1000 * entry_number + k, k = 0..n_trials-1."""
    num = _REGISTRY[entry_id][0]
    return [1000 * num + k for k in range(n_trials)]


def inject(rows: list[dict], entry_id: str, trial_seed: int,
           other_parties: list[dict] | None = None) -> tuple[list[dict], dict]:
    if entry_id not in _REGISTRY:
        raise KeyError(entry_id)
    rng = np.random.default_rng(int(trial_seed))
    out = copy.deepcopy(list(rows))
    fmt = _Fmt(out)
    # background replica jitter (identical protocol for NULL and fault trials)
    for r in out:
        r["kappa"] = fmt.num("kappa", r["kappa"] * float(np.exp(rng.normal(0, BACKGROUND_SIGMA))))
    truth = _REGISTRY[entry_id][1](out, rng, fmt, dict(other_parties=other_parties))
    perm = rng.permutation(len(out))
    out = [out[i] for i in perm]
    truth.update(trial_seed=int(trial_seed), background_sigma=BACKGROUND_SIGMA,
                 background_method_off_run_ids=_background_method_off(out), h_cut=H_CUT)
    for key in ("affected_run_ids", "added_run_ids"):
        truth[key] = sorted(set(truth[key]))
    return out, truth


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def _synthetic_table(seed: int = 7) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(40):
        b = f"PB{p // 8 + 1}"
        x = round(float(rng.uniform(0.05, 0.95)), 3)
        T = float(round(rng.uniform(300, 1200)))
        s = 1001 + p
        inv_inf = 0.05 + 3.6e-5 * (T - 300) + 1.6 * x * (1 - x)
        for n in (24, 48, 96):
            k = 1.0 / (inv_inf + 7.2 / n) * float(np.exp(rng.normal(0, 0.01)))
            rows.append(dict(run_id=f"{b}_x{x}_T{T:g}_n{n}_s{s}", batch_id=b, party="CHPC-MD-C",
                             x=x, T=T, ncz=n, seed=s, kappa=round(k, 4), n_atoms=8 * 6 * 6 * n))
    return rows


def _selftest() -> bool:
    import json
    import os
    base = _synthetic_table()
    ids = ["NULL"] + entries()
    here = os.path.dirname(os.path.abspath(__file__))
    cat = os.path.join(here, "fault_catalog.json")
    if os.path.exists(cat):
        with open(cat) as fh:
            cj = json.load(fh)
        assert sorted(e["id"] for e in cj["entries"]) == sorted(entries()), "catalog/module id mismatch"
    for eid in ids:
        for ts in trial_seeds(eid, 3):
            out, truth = inject(base, eid, ts)
            out2, truth2 = inject(base, eid, ts)
            assert out == out2 and json.dumps(truth, sort_keys=True, default=str) == \
                json.dumps(truth2, sort_keys=True, default=str), f"{eid}: not deterministic"
            for r in out:
                assert tuple(sorted(r)) == tuple(sorted(KEYS)), f"{eid}: schema changed {sorted(r)}"
                for k in KEYS:
                    assert type(r[k]) is type(base[0][k]), f"{eid}: type of {k} changed"
                assert np.isfinite(r["kappa"]) and r["kappa"] > 0, f"{eid}: bad kappa"
            assert base == _synthetic_table(), "input mutated"
            if eid != "NULL":
                assert truth["affected_run_ids"] or truth["added_run_ids"], f"{eid}: empty truth"
            print(f"{eid} seed={ts:5d} rows={len(out):3d} affected={len(truth['affected_run_ids']):3d} "
                  f"added={len(truth['added_run_ids']):3d} op={truth['expected_operator']}")
    print("SELF-TEST PASSED")
    return True


if __name__ == "__main__":
    _selftest()
