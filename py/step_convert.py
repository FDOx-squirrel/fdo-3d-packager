"""convert -- Blender (headless): data/raw model -> dist/<slug>/model.obj
(+textures/) + preview.png.

Offline, runs against whatever `fetch` (S2) already put in data/raw/. Reads
data/raw/source_info.json for `slug`/`model_file` (the S2->S3 handoff
contract, see step_fetch.py:build_source_info). Invokes Blender as a
subprocess running py/blender_convert_headless.py (migrated from
blender_convert.py in the sketchfab_fdo_prototype, neighbouring chat),
which imports the model, exports OBJ+MTL with copied textures
(path_mode="COPY"), and renders a fixed-camera preview.png.

Blender's texture copy lands the image files next to model.obj/model.mtl
under whatever names Blender chose (it can rename on collision, so this
step diffs the output directory rather than assuming filenames) and moves
them into textures/ afterwards, rewriting the .mtl's map_* lines to match
-- PRIMER.md A4: textures/ is classification_rules.yaml's `auxiliary` role,
kept out of `documentation`.

Requires a local Blender install (headless-capable), not pip-installable --
see README.md. Not verified against a real Blender in this chat's sandbox
(none available there); see py/blender_convert_headless.py's own docstring
and PRIMER.md S3 for what was and was not checked.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import DATA_RAW, DIST, MTL_TEXTURE_KEYS, load_source_info


def _organize_textures(out_dir: Path, obj_path: Path, mtl_path: Path, preview_path: Path) -> list[str]:
    """Move every file Blender's path_mode="COPY" left in out_dir alongside
    model.obj/model.mtl into out_dir/textures/, and rewrite the .mtl's
    map_* lines to point there. Diff-based (everything in out_dir that is
    not the .obj/.mtl/preview.png) rather than assuming Blender's chosen
    filenames, since it can rename on collision."""
    keep = {obj_path.name, mtl_path.name, preview_path.name}
    texture_names = sorted(
        p.name for p in out_dir.iterdir()
        if p.is_file() and p.name not in keep
    )
    if not texture_names:
        return []

    textures_dir = out_dir / "textures"
    textures_dir.mkdir(exist_ok=True)
    for name in texture_names:
        (out_dir / name).rename(textures_dir / name)

    texture_set = set(texture_names)
    lines = mtl_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        parts = stripped.split(None, 1)
        if len(parts) == 2 and parts[0] in MTL_TEXTURE_KEYS:
            tokens = parts[1].split()
            if tokens and tokens[-1] in texture_set:
                tokens[-1] = f"textures/{tokens[-1]}"
                line = f"{parts[0]} {' '.join(tokens)}"
        new_lines.append(line)
    mtl_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return texture_names


def run(args: argparse.Namespace) -> tuple[bool, str]:
    info = load_source_info()
    model_in = DATA_RAW / info["model_file"]
    if not model_in.exists():
        return False, f"model file from source_info.json not found: {model_in} -- re-run fetch"

    blender_bin = getattr(args, "blender_bin", None) or os.environ.get("BLENDER_BIN", "blender")
    if shutil.which(blender_bin) is None and not Path(blender_bin).exists():
        return False, (
            f"Blender binary '{blender_bin}' not found -- install Blender (headless-capable) "
            "or pass --blender-bin / set BLENDER_BIN (see README.md External requirements)"
        )

    slug = info["slug"]
    out_dir = DIST / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)  # clean slate: no stale textures from a previous convert
    out_dir.mkdir(parents=True)

    obj_path = out_dir / "model.obj"
    mtl_path = out_dir / "model.mtl"
    preview_path = out_dir / "preview.png"

    script = Path(__file__).resolve().parent / "blender_convert_headless.py"
    cmd = [
        blender_bin, "-b", "--python", str(script), "--",
        "--in", str(model_in),
        "--obj-out", str(obj_path),
        "--preview-out", str(preview_path),
    ]
    # check=True: a failed Blender run must stop the pipeline, not be
    # silently swallowed (PRIMER.md A3: copied subprocess calls keep their
    # check=True guards). main.py's own exception handling reports it.
    subprocess.run(cmd, check=True)

    if not obj_path.exists():
        return False, f"Blender ran but did not produce {obj_path}"
    if not preview_path.exists():
        return False, f"Blender ran but did not produce {preview_path}"

    texture_names: list[str] = []
    if mtl_path.exists():
        texture_names = _organize_textures(out_dir, obj_path, mtl_path, preview_path)

    texture_note = f", {len(texture_names)} texture(s) -> textures/" if texture_names else ""
    return True, f"converted {slug} -> {obj_path.relative_to(DIST.parent)}{texture_note}, {preview_path.name}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender-bin", default=os.environ.get("BLENDER_BIN", "blender"))
    ok, message = run(ap.parse_args())
    print(f"[convert] {message}")
    raise SystemExit(0 if ok else 1)
