"""Crop each full TRIM window capture to its panels (drops the empty grey area).
Usage: python3 crop_screens.py   (needs Pillow)"""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent / "screens"
for p in sorted(HERE.glob("*_trim_window.png")):
    im = Image.open(p)
    # panels sit in the top-left 945 x 815 px of the 1936 x 1168 maximised window
    im.crop((0, 0, min(945, im.width), min(815, im.height))).save(
        p.with_name(p.name.replace("_trim_window", "_trim_plot")))
    print(p.name, im.size)
