"""Write GUI variants of the committed TRIM.IN inputs for screenshots.

Same ion, energy and target as the batch runs in ../srim_inputs. Only three
fields change: ion count (fewer, for a readable plot), cascade type (2 = full
damage cascade, so recoil tracks are drawn) and plot type (0 = ion and recoil
tracks projected on the depth-Y plane, the standard TRIM view).
Usage: python make_gui_inputs.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "srim_inputs"
OUT = HERE / "inputs"
# recipe -> number of ions shown (Kr cascades are dense, so fewer ions)
RECIPES = {
    "He_Si0.8Ge0.2_40keV": 1000,
    "C_Si0.8Ge0.2_40keV": 1000,
    "He_Si_40keV": 1000,
    "Kr_Si_500keV": 100,
}

for name, n in RECIPES.items():
    lines = (SRC / f"{name}.TRIM.IN").read_text().splitlines()
    f = lines[2].split()           # Z1 M1 E angle N bragg autosave
    f[4], f[6] = str(n), str(n + 1)
    lines[2] = "     " + "   ".join(f)
    c = lines[4].split()           # cascade type, seed, reminders
    c[0] = "2"
    lines[4] = "                      " + "                                   ".join(c[:2]) + "       " + c[2]
    p = lines[10].split()          # plot type, xmin, xmax
    p[0] = "0"
    lines[10] = "       " + "                         ".join(p)
    (OUT / f"{name}.TRIM.IN").write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))
    print(name, n)
