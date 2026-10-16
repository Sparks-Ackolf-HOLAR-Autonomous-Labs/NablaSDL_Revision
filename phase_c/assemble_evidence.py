#!/usr/bin/env python3
"""Assemble the three-party fitting table from the evidence hypergraph.

Reads ../pilot/kg/extracted_points.json (90 points: literature + DGX-MD
+ CHPC-MD) and writes evidence_table.json with per-party scope labels:

- literature rows (numeric corpusId): scope "literature-bulk"; rows
  without both x and T are kept but flagged unusable for fitting;
- MD rows (corpusId DGX-MD / CHPC-MD): raw finite-size points get scope
  "tersoff-md-finite-size" (never fit directly against bulk data);
  where a (party-pooled) size series has >= 3 lengths, a 1/L
  extrapolated row is added with scope "tersoff-md-extrapolated",
  which is the MD party's fitting scope.

Pure stdlib. Usage: python3 assemble_evidence.py
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
KG = os.path.join(HERE, "..", "pilot", "kg", "extracted_points.json")


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    return my - b * mx, b


def main():
    raw = json.load(open(KG))
    rows, md = [], {}
    for p in raw:
        cid = str(p.get("corpusId"))
        party = cid if cid in ("DGX-MD", "CHPC-MD") else "literature"
        x, T, k = p.get("x_ge"), p.get("T_K"), p.get("kappa_W_mK")
        if party == "literature":
            rows.append({
                "party": "literature", "scope": "literature-bulk",
                "x": x, "T": T, "kappa": k,
                "fit_usable": bool(x is not None and T is not None and k),
                "source": cid, "title": p.get("title"),
            })
        else:
            # snippet_hash e.g. "x0.5_T300_z96_s101" carries the size
            m = re.match(r"x([\d.]+)_T(\d+)_z(\d+)_s(\d+)", p["snippet_hash"])
            ncz = int(m.group(3)) if m else None
            rows.append({
                "party": party, "scope": "tersoff-md-finite-size",
                "x": x, "T": T, "kappa": k, "ncz": ncz,
                "fit_usable": False,
                "source": p["snippet_hash"],
            })
            if ncz:
                md.setdefault((x, T), {}).setdefault(ncz, []).append(k)

    # 1/L extrapolated MD rows (pooled over machines: protocol-identical)
    for (x, T), series in sorted(md.items()):
        if len(series) < 3:
            continue
        xs, inv = [], []
        for ncz, ks in series.items():
            kmean = len(ks) / sum(1.0 / k for k in ks)
            xs.append(1.0 / ncz)   # 1/L up to the lattice constant
            inv.append(1.0 / kmean)
        a, b = fit(xs, inv)
        if a <= 0:
            continue
        # ballistic guard: if the extrapolation is a large multiple of the
        # biggest finite-size value, the series has not left the linear
        # regime (pure Ge's nominal 238 W/mK); trend evidence only
        kmax = max(k for ks in series.values() for k in ks)
        if 1.0 / a > 3.0 * kmax:
            continue
        rows.append({
            "party": "MD-extrapolated", "scope": "tersoff-md-extrapolated",
            "x": x, "T": T, "kappa": round(1.0 / a, 3),
            "n_lengths": len(series), "fit_usable": True,
            "source": "1/L extrapolation over pooled DGX+CHPC series",
        })

    out = os.path.join(HERE, "evidence_table.json")
    with open(out, "w") as f:
        json.dump(rows, f, indent=2)
    parties = {}
    for r in rows:
        parties[r["party"]] = parties.get(r["party"], 0) + 1
    usable = sum(1 for r in rows if r["fit_usable"])
    print(f"{len(rows)} rows -> {out}; by party {parties}; "
          f"{usable} fit-usable")


if __name__ == "__main__":
    main()
