"""TRIM-style diagrams from the saved SRIM text outputs, plus RustBCA tracks.

No SRIM rerun. Inputs:
  ../srim_raw/<recipe>_RANGE_3D.txt   final position of every ion (SRIM)
  ../srim_raw/<recipe>_VACANCY.txt    vacancies per angstrom per ion (SRIM, Kinchin-Pease)
  <rustbca_dir>/prof_<recipe>_deposited.output    20 000-ion RustBCA ranges
  <rustbca_dir>/traj_<recipe>_trajectories.output  RustBCA ion + recoil tracks
RustBCA inputs are ../rustbca_run/<recipe>.toml, with only the ion count and
the three track_* switches changed for the track runs (run_rustbca_tracks.sh).
Usage: python3 make_trim_style.py <rustbca_dir>
"""
import re, sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "srim_raw"
RB = Path(sys.argv[1]) if len(sys.argv) > 1 else None
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                     "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7})
ION_C, SI_C, GE_C, RB_C = "#d62728", "#1f77b4", "#ff7f0e", "#2ca02c"


def read_range3d(rec):
    rows = []
    for ln in (RAW / f"{rec}_RANGE_3D.txt").read_text(errors="ignore").splitlines():
        p = ln.split()
        if len(p) == 4 and re.fullmatch(r"\d{7}", p[0]):
            rows.append([float(v) for v in p[1:]])
    return np.array(rows) / 10.0  # angstrom -> nm


def read_vacancy(rec):
    rows = []
    for ln in (RAW / f"{rec}_VACANCY.txt").read_text(errors="ignore").splitlines():
        p = ln.split()
        if len(p) == 3:
            try:
                rows.append([float(v) for v in p])
            except ValueError:
                pass
    a = np.array(rows)
    return a[:, 0] / 10.0, a[:, 1] + a[:, 2]  # depth nm, vacancies/(A ion)


def read_csv_fast(path, ncol):
    a = np.fromstring(Path(path).read_text().replace("\n", ","), sep=",")
    return a.reshape(-1, ncol)


def label(rec):
    ion, tgt, e = rec.split("_")
    return f"{ion} {e} into {tgt.replace('Si0.8Ge0.2', 'Si$_{0.8}$Ge$_{0.2}$')}"


def ion_z(rec):
    return {"He": 2, "C": 6, "Kr": 36}[rec.split("_")[0]]


def tracks_panel(ax, rec, xmax):
    t = read_csv_fast(RB / f"traj_{rec}_trajectories.output", 6)
    n = np.loadtxt(RB / f"traj_{rec}_trajectory_data.output", dtype=int, ndmin=1)
    ends = np.cumsum(n)
    starts = ends - n
    zion = ion_z(rec)
    segs = {14: [], 32: [], zion: []}
    for s, e in zip(starts, ends):
        if e - s < 2:
            continue
        z = int(t[s, 1])
        segs.setdefault(z, []).append(t[s:e, 3:5] * 1e3)  # micron -> nm
    # recoil cascades first, ion paths drawn on top
    for z, col, lw, lab in [(14, SI_C, 0.3, "Si recoils"), (32, GE_C, 0.3, "Ge recoils"),
                            (zion, ION_C, 0.5, "ion")]:
        if segs.get(z):
            ax.add_collection(LineCollection(segs[z], colors=col, linewidths=lw,
                                             label=lab, rasterized=True))
    allxy = np.vstack([s for v in segs.values() for s in v])
    ax.set_xlim(0, xmax)
    ylim = np.percentile(np.abs(allxy[:, 1]), 99.5) * 1.1
    ax.set_ylim(-ylim, ylim)
    ax.set_xlabel("depth (nm)")
    ax.set_ylabel("lateral y (nm)")
    ax.set_title(f"(a) RustBCA ion and recoil tracks, {len(n) and int((t[starts,1]==zion).sum())} ions")
    ax.legend(loc="upper right", frameon=False)


def figure_recipe(rec, out, figsize=(7.0, 5.2)):
    r3 = read_range3d(rec)
    dep = read_csv_fast(RB / f"prof_{rec}_deposited.output", 6)[:, 2] * 1e3
    xmax = 1.08 * max(np.percentile(r3[:, 0], 99.9), np.percentile(dep, 99.9))
    fig, axs = plt.subplots(2, 2, figsize=figsize, constrained_layout=True)
    tracks_panel(axs[0, 0], rec, xmax)
    ax = axs[0, 1]
    ax.scatter(r3[:, 0], r3[:, 1], s=0.4, c=ION_C, alpha=0.5, rasterized=True)
    ax.set_xlim(axs[0, 0].get_xlim()); ax.set_ylim(axs[0, 0].get_ylim())
    ax.set_xlabel("depth (nm)"); ax.set_ylabel("lateral y (nm)")
    ax.set_title(f"(b) SRIM final positions, {len(r3)} stopped ions")
    ax = axs[1, 0]
    bins = np.linspace(0, axs[0, 0].get_xlim()[1], 60)
    ax.hist(r3[:, 0], bins=bins, density=True, histtype="step", color=ION_C, lw=1.2,
            label=f"SRIM, Rp {r3[:,0].mean():.0f} nm")
    ax.hist(dep, bins=bins, density=True, histtype="step", color=RB_C, lw=1.2,
            label=f"RustBCA, Rp {dep.mean():.0f} nm")
    ax.set_xlabel("depth (nm)"); ax.set_ylabel("stopped ions (normalised)")
    ax.set_title("(c) ion range profile, two codes")
    ax.legend(frameon=False)
    ax = axs[1, 1]
    d, v = read_vacancy(rec)
    ax.plot(d, v, color="k", lw=1.0)
    ax.set_xlim(axs[0, 0].get_xlim()); ax.set_ylim(bottom=0)
    ax.set_xlabel("depth (nm)"); ax.set_ylabel("vacancies / (Å ion)")
    ax.set_title("(d) SRIM vacancy profile (Kinchin-Pease)")
    fig.suptitle(label(rec), fontsize=9)
    fig.savefig(f"{out}.png", dpi=250)
    fig.savefig(f"{out}.pdf", dpi=250)
    plt.close(fig)
    return {"recipe": rec, "srim_Rp_nm": round(float(r3[:, 0].mean()), 1),
            "srim_dRp_nm": round(float(r3[:, 0].std()), 1),
            "rustbca_Rp_nm": round(float(dep.mean()), 1),
            "rustbca_dRp_nm": round(float(dep.std()), 1)}


def gallery(out):
    recs = sorted({p.name.split("_RANGE_3D")[0] for p in RAW.glob("*_RANGE_3D.txt")},
                  key=lambda r: (r.split("_")[0], r.split("_")[1], int(r.split("_")[2][:-3])))
    ncol = 4
    nrow = -(-len(recs) // ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(7.0, 1.55 * nrow), constrained_layout=True)
    for ax, rec in zip(axs.flat, recs):
        r3 = read_range3d(rec)
        ax.scatter(r3[:, 0], r3[:, 1], s=0.2, c=ION_C, alpha=0.4, rasterized=True)
        ax.set_title(label(rec), fontsize=7)
        ax.set_xlim(0, np.percentile(r3[:, 0], 99.9) * 1.1)
        ax.tick_params(labelsize=6)
    for ax in axs.flat[len(recs):]:
        ax.axis("off")
    fig.supxlabel("depth (nm)", fontsize=8); fig.supylabel("lateral y (nm)", fontsize=8)
    fig.savefig(f"{out}.png", dpi=250)
    fig.savefig(f"{out}.pdf", dpi=250)
    plt.close(fig)


if __name__ == "__main__":
    gallery(HERE / "fig_srim_final_positions_all")
    stats = []
    if RB is not None:
        for p in sorted(RB.glob("traj_*_trajectories.output")):
            rec = p.name[len("traj_"):-len("_trajectories.output")]
            stats.append(figure_recipe(rec, HERE / f"fig_trimstyle_{rec}"))
            print(stats[-1])
    (HERE / "trimstyle_stats.json").write_text(json.dumps(stats, indent=1))
