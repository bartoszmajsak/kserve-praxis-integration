#!/usr/bin/env python3
"""PNG copies of the light figures, for places that do not take SVG.

Usage: png.py          render docs/figs/NAME.svg to docs/figs/png/NAME.png
       png.py --check  fail when a PNG was rendered from an older version of its figure

Rendering needs `rsvg-convert`, which the rest of the build does not. The PNG files are
committed, and `manifest.json` next to them records the hash of the SVG each one was
rendered from, so the check runs without the renderer.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

FIGS = Path(__file__).resolve().parent.parent / "docs" / "figs"
OUT = FIGS / "png"
MANIFEST = OUT / "manifest.json"
WIDTH = 2080  # twice the width the figures are drawn at


def sources():
    return {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIGS.glob("*.svg")) if not p.stem.endswith("-dark")}


def render():
    if not shutil.which("rsvg-convert"):
        sys.exit("png: rsvg-convert is not installed (package librsvg)")
    OUT.mkdir(exist_ok=True)
    wanted = sources()
    for old in OUT.glob("*.png"):
        if old.stem not in wanted:
            old.unlink()
    for name in wanted:
        subprocess.run(["rsvg-convert", "-w", str(WIDTH), str(FIGS / f"{name}.svg"), "-o", str(OUT / f"{name}.png")], check=True)
    MANIFEST.write_text(json.dumps(wanted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rendered {len(wanted)} figures to {OUT}")


def check():
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    wanted = sources()
    stale = sorted(name for name in wanted if recorded.get(name) != wanted[name] or not (OUT / f"{name}.png").exists())
    extra = sorted(set(recorded) - set(wanted))
    if stale or extra:
        sys.exit(f"png: out of date, run 'make png' and commit the result (changed: {stale}, removed: {extra})")
    print("docs/figs/png is up to date")


if __name__ == "__main__":
    check() if sys.argv[1:] == ["--check"] else render()
