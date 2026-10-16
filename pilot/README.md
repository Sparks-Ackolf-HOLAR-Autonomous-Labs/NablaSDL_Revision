# mat_theory DGX pilot (2026-09-25)

Aim: test runs on the DGX first, with early piloting results before any
CHPC runs; Asta for literature data and an LLM to extract data and build
(hyper) knowledge graphs.

Results summary: `PILOT_REPORT.md`. Everything here ran on the DGX Spark
(GB10, aarch64), CPU only, without touching the
resident vLLM server's GPU memory (the vLLM server was used for inference
in Pilot C, which is what it is there for).

## Layout

- `src/` — pilot code
  - `ledger.py` — append-only hash-chained campaign record, Merkle batch commitments,
    set-membership proofs (integrity layer from `../02_zk_verifiable_computation.md`)
  - `simulator.py` — mock kappa_L(x,T) evidence party with coverage-designed
    seeding, injectable biased batch, and a genuine richer-world anomaly above
    1000 K
  - `minisr.py` — deterministic exhaustive-subset symbolic regression on a
    physical basis library; BIC front selection; support-region and
    ensemble-disagreement passports. Exact clean retrain by construction
    (PySR replaces this at CHPC scale; the interface is what carries over)
  - `ees.py` — shard priority score, greedy hypergraph-transversal targeting
    (with exact brute-force check at pilot scale), forget and scope-limit
    executors with verification evidence objects
  - `run_pilot.py` — Phase A end-to-end campaign (fault + null control)
  - `lammps_pilot.py` — real LAMMPS/Tersoff bring-up: lattice/cohesive-energy
    validation and MD throughput benchmark
  - `mp_kappa.py` — Muller-Plathe rNEMD kappa point (the working method;
    minutes per point)
  - `gk_kappa.py` — Green-Kubo attempt, kept as a record: stock LAMMPS
    Tersoff has no centroid/stress/atom, so GK is not available here
- `results/` — pilot outputs (`pilot_summary.json`, campaign records, `lammps_pilot.json`,
  `gk_kappa_points.json`)
- `kg/` — Pilot C: Asta snippet searches (`kg/asta/q20..q23`), LLM-extracted
  datapoints (`extracted_points.json`), and the evidence hypergraph
  (`kg_hypergraph.json`, `.graphml`, `.png`) built per design element 3
  (regimes, papers, methods, systems as vertices; datapoints as hyperedges)

## Reproducing on the DGX

```bash
python3 -m venv venv && ./venv/bin/pip install numpy scipy scikit-learn networkx matplotlib lammps pysr
# LAMMPS pip wheel needs an MPI runtime; without sudo, extract into user space:
apt-get download libmpich12 libhwloc15 libpmix2t64 libmunge2 libevent-core-2.1-7t64 libevent-pthreads-2.1-7t64
for d in *.deb; do dpkg -x "$d" mpichlib; done
export LD_LIBRARY_PATH=$PWD/mpichlib/usr/lib/aarch64-linux-gnu:$PWD/mpichlib/lib/aarch64-linux-gnu

python src/run_pilot.py results          # Phase A mock campaign (seconds)
python src/lammps_pilot.py results 8     # Tersoff validation + benchmark (~1 min)
python src/mp_kappa.py 0.5 300 out.json 4 24  # one MP kappa point (~10-15 min)
python kg/extract_kg.py kg               # LLM extraction + hypergraph build
```
