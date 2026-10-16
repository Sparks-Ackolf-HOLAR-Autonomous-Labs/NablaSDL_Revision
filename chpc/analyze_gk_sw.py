#!/usr/bin/env python3
"""Turn one in.gk_si_sw run (log + hcacf) into a kappa JSON point.

Usage: analyze_gk_sw.py <run.log> <run.hcacf> <out.json>

Green-Kubo: kappa_aa = V/(kB T^2) * int <J_a(0) J_a(t)> dt, with the
LAMMPS heat/flux output F = J*V, so kappa_aa = 1/(V kB T^2) * int
<F_a(0)F_a(t)> dt. The .hcacf file's last block is the running-averaged
autocorrelation over the whole production run; integrate it cumulatively
(trapezoid) and report the direction-averaged kappa(t) curve, its value
at the full window, and a plateau estimate (mean over the second half of
the window, where the SW-Si HCACF has decayed). Stdlib only.
"""
import json
import sys

KB = 1.3806504e-23
EV2J = 1.602176634e-19
CONVERT = EV2J * EV2J / 1e-12 / 1e-10  # (eV Ang/ps)^2 * ps -> J W/(m K) units


def main():
    logf, hcacff, outf = sys.argv[1], sys.argv[2], sys.argv[3]
    meta = {}
    for line in open(logf):
        p = line.split()
        if not p:
            continue
        if p[0] == "GKS_KXYZ":
            meta["k_indeck_xyz"] = [float(v) for v in p[1:4]]
        elif p[0] == "GKS_KAVE":
            meta["k_indeck_ave"] = float(p[1])
        elif p[0] == "GKS_BOX":
            meta["box"] = [float(v) for v in p[1:4]]
        elif p[0] == "GKS_NATOMS":
            meta["natoms"] = int(p[1])
        elif p[0] == "GKS_META":
            kv = p[1:]
            meta.update({kv[i]: kv[i + 1] for i in range(0, len(kv), 2)})

    # last running-averaged correlation block: Index TimeDelta Ncount J1J1 J2J2 J3J3
    blocks, cur = [], []
    for line in open(hcacff):
        if line.startswith("#"):
            continue
        p = line.split()
        if len(p) == 2:  # "timestep Nrows" header starts a new block
            cur = []
            blocks.append(cur)
        elif len(p) == 6:
            cur.append((float(p[1]), float(p[3]), float(p[4]), float(p[5])))
    acf = blocks[-1]

    dt = 0.001  # ps
    vol = meta["box"][0] * meta["box"][1] * meta["box"][2]  # Ang^3
    T = float(meta["T"])
    scale = CONVERT / (KB * T * T * vol) * dt
    t_ps, k_ave = [], []
    integ = [0.0, 0.0, 0.0]
    prev = acf[0]
    for row in acf:
        for a in range(3):
            integ[a] += 0.5 * (prev[1 + a] + row[1 + a]) * (row[0] - prev[0])
        prev = row
        t_ps.append(row[0] * dt)
        k_ave.append(sum(integ) / 3.0 * scale)

    half = [k for t, k in zip(t_ps, k_ave) if t >= t_ps[-1] / 2]
    plateau = sum(half) / len(half)
    result = {
        "x": 0.0, "T": T,
        "ncell": int(meta["ncell"]), "seed": int(meta["seed"]),
        "method": "Green-Kubo (SW, centroid heat flux)",
        "party": "CHPC-MD", "machine": "notchpeak-guest",
        "natoms": meta["natoms"],
        "box_A": [round(v, 2) for v in meta["box"]],
        "kappa_W_mK": round(plateau, 3),
        "kappa_full_window_W_mK": round(k_ave[-1], 3),
        "kappa_indeck_ave_W_mK": meta.get("k_indeck_ave"),
        "window_ps": t_ps[-1],
        "kappa_vs_t": [[round(t, 2), round(k, 3)]
                       for t, k in zip(t_ps, k_ave)][::200],
        "note": ("feasibility test for the endpoint strategy: SW "
                 "potential, not Tersoff; not directly comparable to "
                 "the alloy party"),
    }
    with open(outf, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "kappa_vs_t"}))


if __name__ == "__main__":
    main()
