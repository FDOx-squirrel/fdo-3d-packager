#!/usr/bin/env python3
"""Seeds data/raw/ci-smoke/ -- CI's stand-in for a real `fetch` run.

`fetch` itself stays untested in CI (network=True, needs a Sketchfab
token, PRIMER.md A3) -- this writes exactly the handoff contract a real
fetch would (source_info.json, see step_fetch.py:build_source_info() and
fdo_3d_packager_utils.py:load_source_info()), by hand, so `convert`
onwards can run against it unmodified. All three required fields
(title/creator/licence) are filled in -- no `todo_placeholders`, so
`--strict` stays green on this fixture for reasons that have nothing to
do with S9 itself.

`model_file` points at a placeholder `.glb` whose *content* is never read
-- `fake_blender.py` (this directory) only checks that it exists, same as
the real Blender step_convert.py wraps only ever checks existence before
handing off to the binary. `texture.jpg` is real enough to be copied
byte-for-byte by `_copy_textures_from_raw()` (step_convert.py) once
`fake_blender.py`'s .mtl references it -- exercises that code path in CI
too, not just the no-texture branch.

`creator_profile` is deliberately filled in, even though it's an optional
field this repo's own schema (`schemas/md_cff/MD.cff-schema.yaml`,
`idLabelEntityOptionalId`) explicitly allows omitting: a first version of
this fixture left it unset (a legitimate case, e.g. a real `--local` fetch
without `--creator-profile`) and `build_fdo` failed against `fdo-squirrel`
with `creators[0] must contain keys 'id' and 'label'` -- `fdo-squirrel`'s
own crosswalk hard-requires both, contradicting its own schema's
"optional id" for exactly this field (PRIMER.md S9 finding, fix belongs in
`fdo-squirrel`, not here). Filling it in here keeps this workflow testing
this repo's own wiring rather than tripping over that upstream bug on
every run; the bug itself is real and documented in PRIMER.md, not
swept under the rug.

Run from the repository root: `python .github/ci-fixtures/seed_fixture.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SLUG = "ci-smoke"
RAW_DIR = REPO_ROOT / "data" / "raw" / SLUG

SOURCE_INFO = {
    "input_mode": "local",
    "slug": SLUG,
    "model_file": f"{SLUG}/model.glb",
    "title": "CI Smoke Test Model",
    "description": "Synthetic fixture seeded by .github/ci-fixtures/seed_fixture.py -- not a real 3D scan.",
    "creator": "fdo-3d-packager CI",
    "creator_profile": "https://github.com/FDOx-squirrel/fdo-3d-packager",
    "licence": "CC-BY-4.0",
    "licence_url": "https://creativecommons.org/licenses/by/4.0/",
    "source_url": None,
    "sketchfab_uid": None,
    "source_note": "Generated for CI, PRIMER.md S9 -- see seed_fixture.py.",
    "todo_placeholders": [],
}


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "model.glb").write_bytes(b"fake_blender.py never reads this content\n")
    (RAW_DIR / "texture.jpg").write_bytes(b"fake_blender.py's .mtl references this filename, not its bytes\n")
    (RAW_DIR / "source_info.json").write_text(
        json.dumps(SOURCE_INFO, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"seed_fixture.py: wrote {RAW_DIR.relative_to(REPO_ROOT)}/ "
          f"(source_info.json, model.glb, texture.jpg)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
