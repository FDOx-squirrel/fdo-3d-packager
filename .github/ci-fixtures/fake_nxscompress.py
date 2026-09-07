#!/usr/bin/env python3
"""CI stand-in for nxscompress -- see fake_nxsbuild.py in this directory
for the full reasoning, identical here.

Invoked exactly like real nxscompress (see step_nexus.py):

    fake_nxscompress.py <model.nxs> -o <model.nxz>
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    argv = sys.argv[1:]
    if "-o" not in argv:
        print("fake_nxscompress.py: missing -o <output>", file=sys.stderr)
        return 1
    nxs_in = argv[0] if argv and not argv[0].startswith("-") else None
    out_path = Path(argv[argv.index("-o") + 1])

    if nxs_in and not Path(nxs_in).exists():
        print(f"fake_nxscompress.py: input not found: {nxs_in}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"fake_nxscompress.py placeholder -- not a real .nxz file\n")
    print(f"fake_nxscompress.py: wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
