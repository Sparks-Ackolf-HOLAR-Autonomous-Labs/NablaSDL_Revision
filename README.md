# Graded revision lets autonomous campaigns update symbolic laws of SiGeC semiconductors from mixed-fidelity evidence

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23413459.svg)](https://doi.org/10.5281/zenodo.23413459)

Code, data and figure scripts for the paper "Graded revision lets autonomous campaigns update symbolic laws of SiGeC semiconductors from mixed-fidelity evidence" (Journal of Materials Chemistry A (RSC)). The manuscript itself is not part of this folder.

Licences: code (Python, shell and SLURM scripts) under the MIT License (`LICENSE`); data, result files, figures and text under CC BY 4.0 (`LICENSE-CC-BY-4.0.txt`). Archived third-party datasets keep their own terms and are cited in the paper: the Starrydata slice is CC BY 4.0 (Katsura et al., Sci. Technol. Adv. Mater.: Methods 5, 2506976 (2025), doi:10.1080/27660400.2025.2506976; cite it and the source paper of each curve used), and the Citrine release keeps its published terms.

Every path below is relative to this folder, and every script runs from it. The folder depends on no other folder or repository.

Analysis, figure and checker scripts run on any machine with the Python packages in `requirements.txt`. Acquisition scripts (SLURM job files and run generators) name the cluster paths and simulation binaries (LAMMPS, GPUMD, almaBTE, MACE) used at the time, so re-running a simulation needs those paths edited to the local installation. The recorded outputs of those runs are included, so no simulation has to be repeated to check a result.

Files whose SHA-256 the campaign record stores (designs, pre-registration digests, the scripts and raw outputs they name, and some notes) are kept byte-for-byte as they ran, because any edit would break verification. They keep their original wording, which includes operator decisions with dates, internal step numbers and the run paths of the time. Raw simulation logs are also kept as written.

Terms used in folder names and notes: a *party* is one evidence source of the campaign (for example Tersoff MD, MACE-MP rNEMD, almaBTE first-principles transport or a curated database); a *gate* is the acceptance check a run must pass before its result enters the campaign record; `phase_c/` holds the main campaign and `pilot/` the campaign-record library and the first trial campaign.

## Campaign material

| path | what it holds |
|---|---|
| `pilot` | evidence hypergraph, LLM literature extraction, campaign-record library, GPU pilot run |
| `chpc` | Tersoff rNEMD campaign on CHPC (finite size, seeds, follow-ups) |
| `party4_bte` | almaBTE first-principles kappa party |
| `party4_mace` | MACE-MP rNEMD party, raw and unit-corrected |
| `party5_databases/README.md` | curated-database party (Citrine, Starrydata) entry rules |
| `party5_databases/ingest_citrine.py` | Citrine ingest |
| `party5_databases/citrine_thermal_conductivity.json.gz` | pinned Citrine release |
| `party5_databases/party5_points.json` | Citrine points used |
| `party5_databases/open_db` | Starrydata pinned slice and ingest |
| `phase_c` | campaign record, CHD stage-0, SR engines and HG-SR, fault study, detector v2, shard action, final law, transfer law, acquisition, screening, head-to-head |
| `gpumd/sizefree` | size-free HNEMD witnesses that set the law level |
| `gpumd/validation_results.json` | GPUMD validation gate |
| `nano` | carbon-free nanostructured SiGe campaign |
| `nano_sigec` | nanostructured SiGeC: design, scattering model, MACE carbon energies, small-SiC MD, Si-zone check, light dopants, structures |
| `bond_angles` | bond-angle descriptor separating amorphous probes |

## Figures

Each figure is drawn by one script at its print size and written to `paper/figure_code/figures/` (plus a 600 dpi PNG). Run from this folder with a Python that has numpy, scipy, matplotlib, scikit-learn and ase:

| figure | command |
|---|---|
| `fig_architecture` | `python3 paper/figure_code/regen_figs/fig_architecture.py` |
| `fig_bond_angles` | `python3 paper/figure_code/regen_figs/fig_bond_angles.py` |
| `fig_detector_v2` | `python3 paper/figure_code/regen_figs/fig_detector_v2.py` |
| `fig_final_law` | `python3 paper/figure_code/regen_figs/fig_final_law.py` |
| `fig_finite_size` | `python3 paper/figure_code/regen_figs/fig_finite_size.py` |
| `fig_hgsr_replay` | `python3 paper/figure_code/regen_figs/fig_hgsr_replay.py` |
| `fig_hypergraph` | `python3 paper/figure_code/regen_figs/fig_hypergraph.py` |
| `fig_implant_trimstyle` | `python3 paper/figure_code/regen_figs/fig_implant_trimstyle.py` |
| `fig_kappa_parties` | `python3 paper/figure_code/regen_figs/fig_kappa_parties.py` |
| `fig_sigec` | `python3 paper/figure_code/regen_figs/fig_sigec.py` |
| `fig_sigec_layers` | `python3 paper/figure_code/regen_figs/fig_sigec_layers.py` |
| `fig_sigec_local_strain` | `python3 paper/figure_code/regen_figs/fig_sigec_local_strain.py` |
| `fig_sigec_provenance` | `python3 paper/figure_code/regen_figs/fig_sigec_provenance.py` |
| `fig_sigec_structures` | `python3 paper/figure_code/regen_figs/fig_sigec_structures.py` |

## Notes

- `fig_implant_trimstyle.py` (ESI Figs. S8 to S10) also reads RustBCA ion and recoil tracks, which are not included (about 650 MB of text). Regenerate them with `bash nano_sigec/implant/trim_style/run_rustbca_tracks.sh /path/to/RustBCA <dir>` (RustBCA, https://github.com/lcpp-org/RustBCA; about 40 s on 4 threads; the inputs are `nano_sigec/implant/rustbca_run/*.toml`), then run the script with `TRIMSTYLE_DIR=<dir>` (default `~/mat_theory_trimstyle`). The SRIM panels and all reported ranges come from the included `nano_sigec/implant/srim_raw/` and `rustbca_ranges.json`.

`traced_inputs.json` lists every file each command opened when the folder was built; `FILES.sha256` lists the digest of every file in the folder.
