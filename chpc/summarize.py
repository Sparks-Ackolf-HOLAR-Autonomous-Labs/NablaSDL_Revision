#!/usr/bin/env python3
"""Summarize chpc/results/*.json kappa points: per-(x,T) table sorted by
box length, seed statistics, and 1/L extrapolation (kappa_inf from a
linear fit of 1/kappa vs 1/Lz, the standard MP finite-size treatment)
where three or more lengths exist. Stdlib only. Prints markdown."""
import glob
import json
import os
import sys


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    return my - b * mx, b  # intercept, slope


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results")
    allpts = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
    allpts = [p for p in allpts if "ncz" in p]  # skip GK feasibility points
    if not allpts:
        print("no points found in", d)
        return
    # baseline protocol (4x4 cross-section, swap every 50) feeds the
    # seed stats and 1/L fits; protocol variants are listed separately
    pts = [p for p in allpts
           if p.get("ncxy", 4) == 4 and p.get("swap_every", 50) == 50]
    variants = [p for p in allpts if p not in pts]
    print("| x_Ge | T (K) | ncz | Lz (A) | atoms | seed | kappa (W/mK) |")
    print("|---|---|---|---|---|---|---|")
    groups = {}
    for p in sorted(pts, key=lambda p: (p["x"], p["T"], p["ncz"], p["seed"])):
        print(f"| {p['x']} | {p['T']:.0f} | {p['ncz']} | {p['box_A'][2]} "
              f"| {p['natoms']} | {p['seed']} | {p['kappa_W_mK']} |")
        groups.setdefault((p["x"], p["T"]), []).append(p)

    print("\n### Derived")
    for (x, T), g in sorted(groups.items()):
        seeds = {}
        for p in g:
            seeds.setdefault(p["ncz"], []).append(p["kappa_W_mK"])
        for ncz, ks in seeds.items():
            if len(ks) > 1:
                m = sum(ks) / len(ks)
                sd = (sum((k - m) ** 2 for k in ks) / (len(ks) - 1)) ** 0.5
                print(f"- x={x}, T={T:.0f} K, ncz={ncz}: {len(ks)} seeds, "
                      f"kappa = {m:.3f} +/- {sd:.3f} W/mK")
        # one point per length (seed-averaged) for the 1/L fit; group by
        # ncz, not the equilibrated Lz, which drifts slightly per seed
        by_len = {}
        for p in g:
            by_len.setdefault(p["ncz"], []).append(p)
        if len(by_len) >= 3:
            xs, inv = [], []
            for ps in by_len.values():
                L = sum(p["box_A"][2] for p in ps) / len(ps)
                k = len(ps) / sum(1.0 / p["kappa_W_mK"] for p in ps)
                xs.append(1.0 / L)
                inv.append(1.0 / k)
            a, b = fit(xs, inv)
            if a > 0:
                print(f"- x={x}, T={T:.0f} K: 1/L extrapolation over "
                      f"{len(by_len)} lengths -> kappa_inf = {1.0/a:.2f} W/mK")
            else:
                print(f"- x={x}, T={T:.0f} K: 1/L fit intercept <= 0 "
                      f"(sizes still too far from converged to extrapolate)")

    if variants:
        print("\n### Protocol variants (cross-section / swap-rate probes)")
        print("| x_Ge | T (K) | ncz | ncxy | swap | atoms | seed | kappa (W/mK) |")
        print("|---|---|---|---|---|---|---|---|")
        for p in sorted(variants, key=lambda p: (p["x"], p["T"], p["ncz"],
                                                 p.get("ncxy", 4),
                                                 p.get("swap_every", 50))):
            print(f"| {p['x']} | {p['T']:.0f} | {p['ncz']} | {p.get('ncxy', 4)} "
                  f"| {p.get('swap_every', 50)} | {p['natoms']} | {p['seed']} "
                  f"| {p['kappa_W_mK']} |")


if __name__ == "__main__":
    main()
