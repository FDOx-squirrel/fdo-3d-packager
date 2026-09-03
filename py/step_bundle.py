"""bundle -- assemble dist/<slug>.zip in fdo-squirrel's expected layout.

Target layout (from fdo-squirrel/example_fdo/, confirmed 2026-09-03):

    <slug>.zip
    |-- MD.cff              top level, YAML
    |-- CITATION.cff        top level, YAML
    |-- data/
    |   |-- model/<file>     .obj/.nxs/.nxz etc. -> role "model"
    |   |-- textures/<file>  -> role "auxiliary" (classification_rules.yaml)
    |   `-- images/<file>    preview.png etc. -> role "documentation"
    `-- viewer/<file>        3DHOP miniviewer (html/js/css)

The viewer travels inside this ZIP (PRIMER.md A4, decided 2026-09-03).
classification_rules.yaml has no rule for .html/.js/.css yet -- how
fdo-squirrel handles that (S7, the round-trip step) is a real open question,
to be fixed upstream in fdo-squirrel if it turns out to matter, not worked
around here by pre-populating distributions[] ourselves (A4: that
pre-population is fdo-squirrel's job, not this repo's).

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
    print(f"[bundle] {message}")
    raise SystemExit(0 if ok else 1)
