#!/usr/bin/env python3
"""Run the registered SRIM recipes (implant_design.json, ledger seq 151) on sparksone.

Writes TRIM.IN files with the install cross-check generator (same target
constants), copies them to C:/SRIM-2013/batch_implant, runs TRIM.exe headless
(TRIMAUTO = 1) one recipe at a time and fetches RANGE.txt, VACANCY.txt and
SRIM Outputs/RANGE_3D.txt into srim_raw/. Refuses to run if the design changed.
Usage: python3 run_srim.py [recipe_name ...]
"""
import hashlib, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "../../../.."))
sys.path.insert(0, os.path.join(HERE, "../../second_system/implant_srim/srim"))
import make_trim_in as M  # noqa: E402

DES = os.path.join(HERE, "implant_design.json")
reg = open(os.path.join(HERE, "PREREGISTERED_SHA256")).read().split()[0]
if hashlib.sha256(open(DES, "rb").read()).hexdigest() != reg:
    sys.exit("implant_design.json changed after registration")
D = json.load(open(DES))
M.EL.update({"He": (2, 4.003, 0.0), "Kr": (36, 83.798, 0.0)})
# rough projected ranges (Angstrom) used only to size the target to about 2.5 x range
RP_GUESS = {("He", 20): 2000, ("He", 40): 3800, ("He", 50): 4500, ("He", 80): 6500,
            ("He", 100): 8000, ("He", 160): 11000, ("C", 10): 300, ("C", 20): 600,
            ("C", 40): 1200, ("C", 80): 2200, ("C", 160): 4000, ("Kr", 500): 2600}
EXE = [os.path.join(REPO, "AIR/sparksone/sparksone_exec.sh")]
REMOTE = "C:/SRIM-2013/batch_implant"


def recipes():
    out = []
    for grp in ("A_he_anchor_Si", "A_he_SiGe", "B_c_SiGe", "C_kr_anchor_Si"):
        for ion, e, x in D["recipes"][grp]:
            name = f"{ion}_{'Si' if x == 0 else f'Si{1 - x:g}Ge{x:g}'}_{e}keV"
            out.append((name, ion, e, x, 2000 if ion == "Kr" else 5000, int(2.5 * RP_GUESS[(ion, e)])))
    return out


def ssh_opts():
    key = os.path.expanduser("~/.ssh/sparksone_ci_key")
    return ["-i", key, "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]


def host():
    h = os.environ.get("SPARKSONE_HOST") or subprocess.run(
        "tailscale status | awk '$2 == \"sparksone\" {print $1; exit}'", shell=True,
        capture_output=True, text=True).stdout.strip()
    return f"{os.environ['SPARKSONE_USER']}@{h}"


def ps(cmd, timeout=900):
    r = subprocess.run(EXE + [cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout


def main():
    want = set(sys.argv[1:])
    inp = os.path.join(HERE, "srim_inputs"); raw = os.path.join(HERE, "srim_raw")
    os.makedirs(inp, exist_ok=True); os.makedirs(raw, exist_ok=True)
    ps(f"New-Item -ItemType Directory -Force -Path '{REMOTE}' | Out-Null")
    for name, ion, e, x, n, width in recipes():
        if want and name not in want:
            continue
        f = os.path.join(inp, f"{name}.TRIM.IN")
        open(f, "wb").write(M.trim_in(name, ion, e, x, n_ions=n, width_A=width).encode("ascii"))
        subprocess.run(["scp", "-q"] + ssh_opts() + [f, f"{host()}:{REMOTE}/{name}.TRIM.IN"], check=True)
        t0 = time.time()
        out = ps("Set-Location C:/SRIM-2013; Set-Content -Path TRIMAUTO -Value 1; "
           f"Copy-Item '{REMOTE}/{name}.TRIM.IN' TRIM.IN -Force; "
           "Remove-Item RANGE.txt,VACANCY.txt,'SRIM Outputs/RANGE_3D.txt' -ErrorAction SilentlyContinue; "
           # TRIM occasionally stalls with no CPU use (observed 2026-10-12); kill after 300 s and retry once
           "foreach ($i in 1..2) { $p = Start-Process -FilePath C:/SRIM-2013/TRIM.exe -WorkingDirectory C:/SRIM-2013 -PassThru; "
           "if ($p.WaitForExit(300000)) { break } else { Stop-Process -Id $p.Id -Force; Write-Output 'TRIM_RETRY' } }; "
           f"Copy-Item RANGE.txt '{REMOTE}/{name}_RANGE.txt'; Copy-Item VACANCY.txt '{REMOTE}/{name}_VACANCY.txt'; "
           f"Copy-Item 'SRIM Outputs/RANGE_3D.txt' '{REMOTE}/{name}_RANGE_3D.txt'")
        for suf in ("RANGE", "VACANCY", "RANGE_3D"):
            subprocess.run(["scp", "-q"] + ssh_opts() + [f"{host()}:{REMOTE}/{name}_{suf}.txt",
                                                        os.path.join(raw, f"{name}_{suf}.txt")], check=True)
        print(f"{name}: {time.time() - t0:.0f} s{' (retried)' if 'TRIM_RETRY' in out else ''}", flush=True)


if __name__ == "__main__":
    main()
