# TRIM plot-window captures (2026-10-12)

Two options were produced for SRIM/TRIM pictures (2026-10-12). This folder is
option 2: the TRIM program's own window, captured on
sparksone. Option 1 (diagrams drawn from the saved text outputs) is in
`../trim_style/`.

## What was run

TRIM-2013 on sparksone, same ion, energy and target as the batch recipes in
`../srim_inputs/`. `make_gui_inputs.py` changes three fields only:

| Field | Batch runs | Window runs |
|---|---|---|
| ions | 5000 (Kr 2000) | 1000 (Kr 100) |
| damage | quick Kinchin-Pease | full cascades, so recoil paths are drawn |
| plot type | 5 (no plots) | 0 (ions and recoils, depth vs Y) |

The screens show TRIM's own range and straggle for these smaller runs; the
numbers used anywhere in the papers stay the batch outputs in `../srim_raw/`.

## How the capture works

`drive_gui.ps1` is started by a Windows scheduled task with
`LogonType Interactive`, so TRIM opens in the logged-in desktop session
instead of the SSH session (which has no desktop). It sets `TRIMAUTO` to 0 so
TRIM keeps its window open after the last ion, waits until TRIM stops using
CPU, saves each TRIM window with `PrintWindow`, closes TRIM and puts
`TRIMAUTO` back to its previous value (1, batch mode).

Three things learned on the way (also in the script header):

- The sparksone console has been locked since 2026-10-07 (LogonUI running), so
  a screen grab returns only the lock-screen background. `PrintWindow` with
  `PW_RENDERFULLCONTENT` renders the window itself and works while locked.
- TRIM does not process window messages while it computes, so any synchronous
  window call (ShowWindow, PrintWindow) must wait until the run is finished.
- Under `powershell -File`, an argument `15,40` bound to an `[int]` parameter
  becomes 1540. The script takes one string and splits it on `;`.

To rerun:

```
python3 make_gui_inputs.py
# copy drive_gui.ps1 and inputs/ to C:\Users\admin\trim_gui on sparksone, then
# register a scheduled task (user admin, LogonType Interactive) running
# conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass
#   -File C:\Users\admin\trim_gui\drive_gui.ps1 -RecipeList "a;b" -TimeoutS 240
```

## Files

- `screens/<recipe>_trim_window.png`: the full TRIM window after the last ion
- `screens/<recipe>_trim_plot.png`: the same image cropped to the plot and
  statistics panels
- `logs/*_log.txt`: the driver logs from sparksone (renamed from `.log`, which the repo `.gitignore` drops)
