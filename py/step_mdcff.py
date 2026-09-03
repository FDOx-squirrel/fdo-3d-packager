"""mdcff -- write MD.cff + CITATION.cff, validate against fdo-squirrel's
MD.cff-schema.yaml.

Needs the descriptive metadata from `fetch` (title/creator/licence/source)
and the checksums from `nexus`, so it runs after both. `fdo_type` is fixed
to "fdo:3DDataFDO" (PRIMER.md A4).

distributions[] is deliberately left empty/omitted here: fdo-squirrel scans
the package itself (classification_rules.yaml) rather than trusting a
packager-supplied list (PRIMER.md A4, decided 2026-09-03). If that scan
turns out wrong or incomplete for our output (e.g. the viewer's .html/.js/
.css files), the fix belongs in fdo-squirrel, not as a workaround here.

S1: stub only.
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
    ok, message = run(argparse.Namespace())
    print(f"[mdcff] {message}")
    raise SystemExit(0 if ok else 1)
