#!/usr/bin/env python3
"""CI stand-in for Blender -- PRIMER.md S9.

Blender itself is not available on a GitHub-hosted runner without a heavy
install, and is not this repo's concern to test (that's Blender's own
correctness, not this pipeline's). What *is* this pipeline's concern, and
what CI should actually catch, is the wiring around it: does `convert`
call the binary with the right arguments, handle its absence, find the
files it's supposed to produce, and hand them on correctly to `nexus`?
That's exactly what real Blender wasn't available to test even by hand in
this project's own sandbox sessions (see PRIMER.md S3) -- this fake makes
it testable in CI instead, the same "existence-marker placeholder file"
principle PRIMER.md S5 already used ad hoc, now committed so CI can reuse
it on every run.

Invoked exactly like real Blender is (see step_convert.py and
py/blender_convert_headless.py's own docstring):

    fake_blender.py -b --python <script> -- --in <model> --obj-out <obj> --preview-out <png>

`-b`/`--python <script>` are real Blender's own flags -- ignored here,
this script does not run blender_convert_headless.py at all, it stands in
for the whole `blender` binary. Only `--in`/`--obj-out`/`--preview-out`
(after the `--`) are read.

Writes a minimal but genuinely valid one-triangle OBJ + a companion .mtl
that references `texture.jpg` (matching the CI fixture seeded by
seed_fixture.py) -- deliberately not empty, so `_copy_textures_from_raw()`
in step_convert.py has something real to find and copy, exercising that
code path in CI too, not just the no-texture path. `--preview-out` gets a
minimal valid 1x1 PNG (hardcoded bytes, no imaging library needed).
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

# Smallest valid PNG: 1x1, transparent.
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+A8AAQUBAScY"
    "42YAAAAASUVORK5CYII="
)

_OBJ = """# fake_blender.py CI fixture -- not a real model
mtllib model.mtl
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
usemtl fake
f 1 2 3
"""

_MTL = """newmtl fake
map_Kd texture.jpg
"""


def parse_args() -> dict:
    argv = sys.argv[1:]
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv
    args, key = {}, None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
            args[key] = True
        elif key:
            args[key] = a
            key = None
    return args


def main() -> int:
    args = parse_args()
    model_in = args.get("in")
    obj_out = args.get("obj-out")
    preview_out = args.get("preview-out")
    if not (model_in and obj_out and preview_out):
        print("fake_blender.py: missing --in/--obj-out/--preview-out", file=sys.stderr)
        return 1
    if not Path(model_in).exists():
        print(f"fake_blender.py: --in file not found: {model_in}", file=sys.stderr)
        return 1

    obj_path = Path(obj_out)
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    obj_path.write_text(_OBJ, encoding="utf-8")
    obj_path.with_suffix(".mtl").write_text(_MTL, encoding="utf-8")
    Path(preview_out).write_bytes(_PNG_1X1)

    print(f"fake_blender.py: wrote {obj_path.name}, {obj_path.with_suffix('.mtl').name}, {Path(preview_out).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
