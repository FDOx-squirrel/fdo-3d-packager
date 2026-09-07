"""convert -- Blender (headless): data/raw model -> dist/<slug>/model.obj
(+textures/) + preview.png.

Offline, runs against whatever `fetch` (S2) already put in data/raw/. Reads
data/raw/source_info.json for `slug`/`model_file` (the S2->S3 handoff
contract, see step_fetch.py:build_source_info). Invokes Blender as a
subprocess running py/blender_convert_headless.py (migrated from
blender_convert.py in the sketchfab_fdo_prototype, neighbouring chat),
which imports the model and exports OBJ+MTL (path_mode="STRIP" -- filenames
only, no copy attempt) plus a fixed-camera preview.png.

Befund 2026-09-04: Blender's own path_mode="COPY" turned out unreliable in
a real run (every texture reported "missing", nothing copied -- see
blender_convert_headless.py's docstring). This step now copies the
textures itself: it reads the filenames model.mtl references and copies
them from data/raw/<slug>/ (which step_fetch.py/S2 already guarantees is
complete) into dist/<slug>/textures/, rewriting the .mtl to match --
independent of whatever Blender's own path resolution did or didn't do.
textures/ as its own folder is still intentional either way (PRIMER.md A4:
classification_rules.yaml's `auxiliary` role, kept out of `documentation`).

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


def _copy_textures_from_raw(model_dir_raw: Path, out_dir: Path, mtl_path: Path) -> tuple[list[str], list[str]]:
    """Copy every texture model.mtl references from data/raw/<slug>/ into
    out_dir/textures/, and rewrite the .mtl's map_* lines to point there.

    Befund 2026-09-04: Blender's own path_mode="COPY" turned out unreliable
    (every texture reported "Missing source file" and skipped, even after
    explicitly relinking the image datablocks beforehand -- see
    blender_convert_headless.py:relink_images() for what was tried and its
    diagnostics). What *does* survive intact regardless: Blender still
    writes the correct texture *filename* into each map_* line even when it
    can't copy the bytes. So this reads those filenames back out of
    model.mtl and copies them ourselves from model_dir_raw
    (data/raw/<slug>/, which step_fetch.py/S2 already guarantees holds
    every sibling file, textures included) -- independent of whatever
    Blender's internal path resolution did or didn't do. Returns (copied
    filenames, referenced-but-not-found filenames)."""
    if not mtl_path.exists():
        return [], []

    by_name = {p.name: p for p in model_dir_raw.rglob("*") if p.is_file()}
    textures_dir = out_dir / "textures"

    copied: list[str] = []
    missing: list[str] = []
    new_lines = []
    for line in mtl_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        parts = stripped.split(None, 1)
        if len(parts) == 2 and parts[0] in MTL_TEXTURE_KEYS:
            tokens = parts[1].split()
            if tokens:
                # Strip whatever path Blender did or didn't write (STRIP
                # mode should already leave a bare filename, but this is
                # robust either way) -- only the filename is trustworthy.
                tex_name = Path(tokens[-1]).name
                source = by_name.get(tex_name)
                if source:
                    textures_dir.mkdir(exist_ok=True)
                    shutil.copyfile(source, textures_dir / tex_name)
                    copied.append(tex_name)
                    tokens[-1] = f"textures/{tex_name}"
                    line = f"{parts[0]} {' '.join(tokens)}"
                else:
                    missing.append(tex_name)
        new_lines.append(line)
    mtl_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return copied, missing


def run(args: argparse.Namespace) -> tuple[bool, str]:
    info = load_source_info(getattr(args, "slug", None))
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
    missing_textures: list[str] = []
    if mtl_path.exists():
        texture_names, missing_textures = _copy_textures_from_raw(model_in.parent, out_dir, mtl_path)

    texture_note = f", {len(texture_names)} texture(s) -> textures/" if texture_names else ""
    message = f"converted {slug} -> {obj_path.relative_to(DIST.parent)}{texture_note}, {preview_path.name}"
    if missing_textures:
        message = "Warning: " + message + f" -- {len(missing_textures)} texture(s) referenced in model.mtl not found under {model_in.parent}: {', '.join(missing_textures)}"
    return True, message


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender-bin", default=os.environ.get("BLENDER_BIN", "blender"))
    ap.add_argument("--slug", help="Which fetched model (data/raw/<slug>/) to convert. Auto-detected if exactly one exists.")
    ok, message = run(ap.parse_args())
    print(f"[convert] {message}")
    raise SystemExit(0 if ok else 1)
