"""nexus -- nxsbuild/nxscompress: dist/<slug>/model.obj -> model.nxs -> model.nxz.

Offline, runs against whatever `convert` (S3) already put in
dist/<slug>/: model.obj + model.mtl + textures/ (see step_convert.py).
Reads data/raw/source_info.json for `slug` (the same S2 handoff contract
S3 reads, see step_fetch.py:build_source_info) to find dist/<slug>/.

nxsbuild reads model.obj directly (its mtllib line already points at
textures/<file> relative to model.obj -- see step_convert.py's
_copy_textures_from_raw()) and writes model.nxs into the same folder.
nxscompress then reads model.nxs and writes the compressed model.nxz next
to it. Both are separate binaries from cnr-isti-vclab/nexus, not
pip-installable -- see README.md External requirements.

Requires local nxsbuild/nxscompress binaries. Not verified against real
binaries in this chat's sandbox (neither is available there, and building
Nexus from source needs Qt/vcglib -- out of scope here, reference platform
is Windows per PRIMER.md A3 anyway); see PRIMER.md S4 for what was and was
not checked, same caveat as py/blender_convert_headless.py for S3.
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

from py.fdo_3d_packager_utils import DIST, load_source_info


def _find_binary(explicit: str | None, env_var: str, default_name: str) -> str | None:
    """Resolve a binary the same way step_convert.py resolves --blender-bin:
    explicit CLI flag, else environment variable, else bare name on PATH.
    Returns the resolved string to exec, or None if nothing on disk/PATH
    matches it."""
    candidate = explicit or os.environ.get(env_var, default_name)
    if shutil.which(candidate) is not None or Path(candidate).exists():
        return candidate
    return None


def run(args: argparse.Namespace) -> tuple[bool, str]:
    info = load_source_info()
    slug = info["slug"]
    out_dir = DIST / slug
    obj_path = out_dir / "model.obj"
    if not obj_path.exists():
        return False, f"{obj_path} not found -- run `python main.py --only convert` first"

    nxsbuild_arg = getattr(args, "nxsbuild_bin", None)
    nxsbuild_bin = _find_binary(nxsbuild_arg, "NXSBUILD_BIN", "nxsbuild")
    if nxsbuild_bin is None:
        shown = nxsbuild_arg or os.environ.get("NXSBUILD_BIN", "nxsbuild")
        return False, (
            f"nxsbuild binary '{shown}' not found -- install nxsbuild (cnr-isti-vclab/nexus) "
            "or pass --nxsbuild-bin / set NXSBUILD_BIN (see README.md External requirements)"
        )

    nxscompress_arg = getattr(args, "nxscompress_bin", None)
    nxscompress_bin = _find_binary(nxscompress_arg, "NXSCOMPRESS_BIN", "nxscompress")
    if nxscompress_bin is None:
        shown = nxscompress_arg or os.environ.get("NXSCOMPRESS_BIN", "nxscompress")
        return False, (
            f"nxscompress binary '{shown}' not found -- install nxscompress (cnr-isti-vclab/nexus) "
            "or pass --nxscompress-bin / set NXSCOMPRESS_BIN (see README.md External requirements)"
        )

    nxs_path = out_dir / "model.nxs"
    nxz_path = out_dir / "model.nxz"
    # Idempotency: drop stale outputs from a previous run first, same
    # reasoning as step_convert.py clearing dist/<slug>/ -- but here only
    # the two files this step owns, not the whole folder (model.obj,
    # textures/, preview.png belong to S3 and must survive).
    for stale in (nxs_path, nxz_path):
        stale.unlink(missing_ok=True)

    # check=True: a failed nxsbuild/nxscompress run must stop the pipeline,
    # not be silently swallowed (PRIMER.md A3: copied subprocess calls keep
    # their check=True guards). main.py's own exception handling reports it.
    subprocess.run([nxsbuild_bin, str(obj_path), "-o", str(nxs_path)], check=True)
    if not nxs_path.exists():
        return False, f"nxsbuild ran but did not produce {nxs_path}"

    subprocess.run([nxscompress_bin, str(nxs_path), "-o", str(nxz_path)], check=True)
    if not nxz_path.exists():
        return False, f"nxscompress ran but did not produce {nxz_path}"

    message = f"built {slug} -> {nxs_path.name}, {nxz_path.name}"
    return True, message


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nxsbuild-bin", default=os.environ.get("NXSBUILD_BIN", "nxsbuild"))
    ap.add_argument("--nxscompress-bin", default=os.environ.get("NXSCOMPRESS_BIN", "nxscompress"))
    ok, message = run(ap.parse_args())
    print(f"[nexus] {message}")
    raise SystemExit(0 if ok else 1)
