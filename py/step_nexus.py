"""nexus -- nxsbuild/nxscompress: dist/model.obj -> dist/model.nxs -> model.nxz.

Requires local nxsbuild/nxscompress binaries (cnr-isti-vclab/nexus), not
pip-installable -- see README.md. Offline otherwise.

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
    print(f"[nexus] {message}")
    raise SystemExit(0 if ok else 1)
