# 300 K law level by equilibrium Green-Kubo (follow-up to campaign-record entries 91-102)

Registered at the campaign-record entry in `PREREGISTERED_SHA256` (`gk300_design.json`,
written by `design_gk300.py`), pushed with all scripts (build, commit,
analysis, decision) before any run directory existed. Run 2026-10-07.

Why: two driven-heat-current registrations (campaign-record entries 91/96-98 and 99-102)
stopped at their gates. Long HNEMD cells at 300 K ran away or drifted, so
the 300 K level of the bulk law is carried from 700-1100 K. Equilibrium
Green-Kubo (GPUMD `compute_hac`) reads the same conductivity from
heat-current fluctuations with no driving force.

Stages
- **K1** (38 runs): x = 0.15 and 0.85 at 8^3, 12^3 (6 seeds) and 16^3
  (4 seeds) cells, 300 K; plus x = 0.5 at 700 K, 8^3, 6 seeds as the method
  check against size-free HNEMD (1.87 +/- 0.14 W/mK). Each run: NPT 100 ps,
  NVT 50 ps, NVE 10 ns with the heat-current autocorrelation to 100 ps.
  Read-out: running conductivity averaged over 50-100 ps, mean of x, y, z.
  Gates G_plat (50-75 vs 75-100 ps), G_meth, G_conv (12^3 vs 16^3) select
  box* = 8 or 12.
- **K2-box<box*>** (24 runs): x = 0.2, 0.3, 0.5, 0.7 at box*, 6 seeds.
  `make_runs_gk300.py` refuses any K2 stage other than the one the
  committed K1 analysis selected.

Decision rule (in the design, same branches as campaign-record entries 99): any gate fails,
the 300 K level stays carried; on pass, rho300 = kappa_GK / law at six
compositions gives (a) strengthen, (b) a temperature-dependent level, or
(c) downweight the 300 K composition shape.

A 5-second DGX smoke run (`make_runs_gk300.py K1 --smoke`, 20 ps NVE) checked
the input syntax and the 11-column `hac.out` layout before registration; it
is not design evidence.

Workflow (CHPC side root `~/mat_theory/gpumd_gk300`)
1. `python3 make_runs_gk300.py K1 --out DIR [--placement grn|guest]`, rsync to CHPC, `sbatch`
2. copy the finished runs from CHPC, then `python3 commit_gk300.py K1`, commit + push
3. `python3 analyze_gk300.py` (writes box*), commit + push
4. if box*: build/run/commit `K2-box<box*>` the same way, then re-run the analysis
5. `python3 apply_gk300.py` records the analysis and the shard operation

Submitted 2026-10-07: stage **K1**, 38 runs, CHPC array
**16114861** (notchpeak-gpu-guest, A40, `--exclude=notch168,notch294,notch299`
for the known unusable GPU nodes; a placement detail, not a design change).
Built with `make_runs_gk300.py K1 --placement guest` (design hash checked
against campaign-record entries 107); CHPC root `~/mat_theory/gpumd_gk300`. K2 waits for
the committed K1 analysis.

K1 collected 2026-10-08: 38/38 exit 0 (A40, notch103/426/472/474).
Raw committed at campaign-record entries 111 before analysis. `analyze_gk300.py` crashed on the
`#` header lines of GPUMD's `thermo.out`; the temperature read now skips them
(disclosed deviation, campaign-record entries 112; no change to gates, windows or rule). Gates:
G_plat pass at all 7 points, G_meth pass (GK 2.15 +/- 0.10 vs HNEMD
1.87 +/- 0.14 W/mK at x = 0.5, 700 K), G_conv pass -> **box* = 12**. K1 points
(W/mK, 300 K): x = 0.15: 2.52 / 3.29 / 3.59 (8/12/16 cells); x = 0.85: 6.22 /
7.85 / 8.31. PrK1, PrK2 pass; PrK3 fails (3.29 < 4.60). K2-box12 (24 runs) built
by `make_runs_gk300.py K2-box12 --placement guest` and submitted as CHPC array
**16138929** (notchpeak-gpu-guest A40, same exclusions).

K2-box12 collected 2026-10-09: 24/24 exit 0. Raw committed at
campaign-record entries 113 before analysis; analysis 114; decision 115 = **branch (b),
correct**: rho300 over x = 0.15, 0.2, 0.3, 0.5, 0.7, 0.85 = 1.55, 1.52,
1.77, 2.12, 2.04, 1.92 (median 1.84, cv 0.14), so the 300 K level factor is
1.84 against 1.281 at 700-1100 K, linear in T between 300 and 700 K
(`../corrected_law_gk300.json`). PrK1, PrK2, PrK4 pass; PrK3 fails (as in
K1). GK kappa at 300 K, 12^3 cells (W/mK): 3.29, 2.88, 2.91, 3.36, 4.27,
7.85.
