"""build_fdo -- run dist/<slug>.zip through a local fdo-squirrel instance.

Mirrors fdo-squirrel-registry's own S8 ("Registry als FDO, Release und CI"):
"Der Bundle plus Index plus Shapes werden als ZIP durch fdo-squirrel
geschickt [...] der Rundlauf ist zugleich der beste Integrationstest."
Same principle here -- instead of reimplementing RDF generation, this step
feeds our freshly-built package through fdo-squirrel's own ingest and takes
the resulting fdo-metadata.ttl as proof the package is actually usable, not
just schema-valid.

How fdo-squirrel is invoked here (pip package from GitHub, git submodule, or
an external --fdo-squirrel-path requirement like Blender/nxsbuild) is not
decided yet -- see PRIMER.md Teil D. Whichever it is, this step stays
offline: it runs against the dist/<slug>.zip that `bundle` already produced,
it does not re-fetch from Sketchfab.

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
    print(f"[build_fdo] {message}")
    raise SystemExit(0 if ok else 1)
