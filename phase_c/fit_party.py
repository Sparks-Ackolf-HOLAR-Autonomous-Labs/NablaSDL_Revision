#!/usr/bin/env python3
"""One symbolic loop per evidence party: fit kappa(x, T) on that party's
fit-usable rows, with the two passports, and write claims_<party>.json.

Reuses the pilot's minisr (deterministic exhaustive-basis SR, so the
clean retrain is exact); PySR drops in later on the same claim format.
A party with fewer than MIN_POINTS usable rows is refused by design:
an underdetermined symbolic fit would ledger junk claims.

Usage: python3 fit_party.py <party>     e.g. literature, MD-extrapolated
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pilot", "src"))

from minisr import ensemble, fit_front, select_model, support_region  # noqa: E402
from scope_limit_alloys import active_scope_limits  # noqa: E402

MIN_POINTS = 12

# Parties whose claims sit on Tersoff-MD evidence and therefore inherit
# active scope-limit restrictions from the campaign ledger.
MD_PARTIES = {"MD-extrapolated", "DGX-MD", "CHPC-MD"}


def main():
    party = sys.argv[1] if len(sys.argv) > 1 else "literature"
    rows = json.load(open(os.path.join(HERE, "evidence_table.json")))
    data = [{"x": r["x"], "T": r["T"], "kappa": r["kappa"]}
            for r in rows if r["party"] == party and r["fit_usable"]]
    if len(data) < MIN_POINTS:
        print(f"REFUSED: party {party!r} has {len(data)} usable points "
              f"(< {MIN_POINTS}); an underdetermined fit is not ledgered. "
              f"Fill the grid first (seed campaign).")
        sys.exit(1)

    front = fit_front(data)
    model = select_model(front, len(data))
    dist = support_region(data)
    term_freq, disagreement, _ = ensemble(data, m=12, seed=0)

    # HG-SR extras (sr_compare): per-term hyperedge provenance and
    # blast radius over regime/party edges, when tags are available.
    hg = None
    try:
        sys.path.insert(0, os.path.join(HERE, "sr_compare"))
        import hgsr
        from datasets import regime
        tagged = [{"x": r["x"], "T": r["T"], "L": 0.0, "kappa": r["kappa"],
                   "party": r["party"], "source": str(r.get("source", "?")),
                   "regime": regime(float(r["x"]), float(r["T"]))}
                  for r in rows if r["party"] == party and r["fit_usable"]]
        p = hgsr.provenance(tagged, ["x", "T"])
        hg = {"selected": {k: p["selected"][k] for k in
                           ("names", "coefs", "complexity", "mse")},
              "term_provenance": p["term_provenance"],
              "term_labels": p["term_labels"],
              "blast_radius": p["blast_radius"],
              "covered_regimes": p["covered_regimes"]}
    except Exception as e:                                 # keep legacy path
        hg = {"unavailable": repr(e)}

    xs = [d["x"] for d in data]
    Ts = [d["T"] for d in data]
    # Apply active scope-limit shard operations (ledger_campaign.jsonl):
    # the claimed validity domain is the data range intersected with
    # every active restriction on this party's evidence scope.
    x_lo, x_hi = min(xs), max(xs)
    limits_applied = []
    if party in MD_PARTIES:
        for p in active_scope_limits():
            lo, hi = p["restriction"]["x"]
            x_lo, x_hi = max(x_lo, lo), min(x_hi, hi)
            limits_applied.append(p["op_id"])
    grid = [(x, T) for x in (0.1, 0.3, 0.5, 0.7, 0.9)
            for T in (300, 600, 900, 1200)]
    claims = {
        "party": party,
        "n_points": len(data),
        "validity_domain": {"x": [x_lo, x_hi], "T": [min(Ts), max(Ts)]},
        "scope_limits_applied": limits_applied,
        "pareto_front": [{k: m[k] for k in
                          ("names", "coefs", "complexity", "mse")}
                         for m in front],
        "selected": {k: model[k] for k in
                     ("names", "coefs", "complexity", "mse")},
        "passport_term_frequency": term_freq,
        "passport_probe_grid": [
            {"x": x, "T": T,
             "support_dist": round(dist(x, T), 3),
             "ensemble_disagreement": round(disagreement(x, T), 3)}
            for x, T in grid],
        "hgsr": hg,
    }
    out = os.path.join(HERE, f"claims_{party}.json")
    with open(out, "w") as f:
        json.dump(claims, f, indent=2)
    print(f"party {party}: {len(data)} points, selected "
          f"{' + '.join(model['names'])} (mse {model['mse']:.4g}) -> {out}")


if __name__ == "__main__":
    main()
