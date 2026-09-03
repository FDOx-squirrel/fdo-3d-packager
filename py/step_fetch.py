"""fetch -- resolve --sketchfab/--local into data/raw/.

The only step allowed to touch the network (Sketchfab Data/Download API).
Not part of the default `python main.py` run; call it explicitly:

    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/..."
    python main.py --only fetch --local ./scans/rathealy_kiriengine.glb

S1: stub only. Real implementation (S2) migrates the fetch/download logic
from the sketchfab_fdo_prototype in the neighbouring chat -- Sketchfab Data
API metadata harvest + Download API request, or a local-file copy/validate
-- and writes data/raw/<slug>.<ext> plus a small source_info.json recording
which of the two paths was used, so later steps do not need to re-derive it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import nothing_to_do


def run(args: argparse.Namespace) -> tuple[bool, str]:
    return nothing_to_do()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--sketchfab", metavar="URL")
    src.add_argument("--local", metavar="PATH")
    ok, message = run(ap.parse_args())
    print(f"[fetch] {message}")
    raise SystemExit(0 if ok else 1)
