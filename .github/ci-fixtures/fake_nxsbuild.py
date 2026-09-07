#!/usr/bin/env python3
"""CI stand-in for nxsbuild -- PRIMER.md S9, same reasoning as
fake_blender.py in this directory: nxsbuild/nxscompress (cnr-isti-vclab/
nexus) are not pip-installable and building them from source needs Qt/
vcglib, out of scope for a CI smoke test. This fake does not read or
understand the real .nxs binary format -- it writes placeholder bytes at
the `-o` target, which is all step_nexus.py itself ever checks (file
exists), same "existence-marker" principle PRIMER.md S5 used ad hoc.

Invoked exactly like real nxsbuild (see step_nexus.py):

    fake_nxsbuild.py <model.obj> -o <model.nxs> [-O] [-r <MB>]

`-O`/`-r` are accepted and ignored (real nxsbuild flags, meaningless to a
placeholder writer).
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    argv = sys.argv[1:]
    if "-o" not in argv:
        print("fake_nxsbuild.py: missing -o <output>", file=sys.stderr)
        return 1
    obj_in = argv[0] if argv and not argv[0].startswith("-") else None
    out_path = Path(argv[argv.index("-o") + 1])

    if obj_in and not Path(obj_in).exists():
        print(f"fake_nxsbuild.py: input not found: {obj_in}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"fake_nxsbuild.py placeholder -- not a real .nxs file\n")
    print(f"fake_nxsbuild.py: wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
