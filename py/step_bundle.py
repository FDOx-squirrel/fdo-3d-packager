"""bundle -- assemble dist/<slug>.zip in fdo-squirrel's expected layout.

Target layout (from fdo-squirrel/example_fdo/, confirmed 2026-09-03):

    <slug>.zip
    |-- MD.cff              top level, YAML
    |-- CITATION.cff        top level, YAML
    |-- data/
    |   |-- model/<file>     .obj/.mtl/.nxs/.nxz -> role "model"
    |   |-- textures/<file>  -> role "auxiliary" (classification_rules.yaml)
    |   `-- images/<file>    preview.png -> role "documentation"
    `-- viewer/<file>        3DHOP miniviewer (html/js/css), vendored under
                             assets/3dhop/ -- see that folder's NOTICE.md
                             for provenance/pin and what was trimmed.

The viewer travels inside this ZIP (PRIMER.md A4, decided 2026-09-03).
classification_rules.yaml has no rule for .html/.js/.css (and, found while
implementing this step: none for .mtl either) -- how fdo-squirrel handles
that (S7, the round-trip step) is a real open question, to be fixed
upstream in fdo-squirrel if it turns out to matter, not worked around here
by pre-populating distributions[] ourselves (A4: that pre-population is
fdo-squirrel's job, not this repo's). See PRIMER.md Teil D.

Offline (PRIMER.md A3): reads dist/<slug>/ (written by convert/nexus/mdcff,
S3-S5) and assets/3dhop/ (vendored, not live-fetched), no network. Runs
after convert, nexus and mdcff, and gates on all three having produced
their files -- a bundle assembled before the artefacts it packages exist
would silently ship a stale or incomplete ZIP.

Two of the four dist/<slug>/ inputs are optional and handled gracefully,
not required: textures/ (an untextured model is legitimate, not an
error -- see PRIMER.md S6) and model.mtl (Blender/S3 always writes one
today, but nothing here depends on that continuing to be true).

`--slug` (see fdo_3d_packager_utils.py:resolve_slug()) picks which
fetched/converted/packaged model to bundle when more than one exists
under dist/; auto-detected when exactly one does. `main.py --all-slugs`
loops this step (and any others selected) over every one of them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import DIST, VIEWER_SRC, load_source_info, write_deterministic_zip

# dist/<slug>/ files this step requires to already exist (written by
# convert/S3, nexus/S4 and mdcff/S5) -- the completeness gate below.
# model.mtl and textures/ are deliberately absent from this list: both are
# legitimately optional (see module docstring).
REQUIRED_DIST_FILES = ("MD.cff", "CITATION.cff", "model.obj", "model.nxs", "model.nxz", "preview.png")

# Files under assets/3dhop/ that do NOT travel into the shipped ZIP.
# NOTICE.md is this repo's own vendoring note for maintainers, not part of
# the viewer itself -- everything else under assets/3dhop/ (including
# LICENSE.txt, GPLv3 compliance requires it to ship alongside the code) is
# copied in as-is.
VIEWER_EXCLUDE = {"NOTICE.md"}


def collect_viewer_files() -> list[tuple[str, Path]]:
    """Every file under assets/3dhop/ except VIEWER_EXCLUDE, as
    (viewer/<relative path>, source path) pairs, sorted for determinism
    (filesystem iteration order isn't guaranteed across platforms,
    PRIMER.md A3 -- same reasoning as discover_slugs())."""
    if not VIEWER_SRC.exists():
        return []
    files = sorted(p for p in VIEWER_SRC.rglob("*") if p.is_file() and p.name not in VIEWER_EXCLUDE)
    return [(f"viewer/{p.relative_to(VIEWER_SRC).as_posix()}", p) for p in files]


def collect_bundle_entries(out_dir: Path) -> list[tuple[str, Path]]:
    """Every (arcname, source path) pair the bundle ZIP for one slug
    consists of, in the fixed layout from the module docstring. Assumes
    the completeness gate in run() has already confirmed REQUIRED_DIST_FILES
    exist; only the genuinely optional ones (model.mtl, textures/) get
    their own existence check here."""
    entries: list[tuple[str, Path]] = [
        ("MD.cff", out_dir / "MD.cff"),
        ("CITATION.cff", out_dir / "CITATION.cff"),
    ]

    for name in ("model.obj", "model.mtl", "model.nxs", "model.nxz"):
        path = out_dir / name
        if path.exists():
            entries.append((f"data/model/{name}", path))

    textures_dir = out_dir / "textures"
    if textures_dir.exists():
        for path in sorted(textures_dir.iterdir()):
            if path.is_file():
                entries.append((f"data/textures/{path.name}", path))

    entries.append(("data/images/preview.png", out_dir / "preview.png"))
    entries.extend(collect_viewer_files())
    return entries


def run(args: argparse.Namespace) -> tuple[bool, str]:
    info = load_source_info(getattr(args, "slug", None))
    slug = info["slug"]
    out_dir = DIST / slug

    missing = [name for name in REQUIRED_DIST_FILES if not (out_dir / name).exists()]
    if missing:
        return False, (
            f"{out_dir} is missing {', '.join(missing)} -- run "
            "`python main.py --only convert`, `--only nexus` and `--only mdcff` first"
        )

    viewer_files = collect_viewer_files()
    if not viewer_files:
        return False, (
            f"{VIEWER_SRC} not found or empty -- the vendored 3DHOP viewer is missing from this "
            "checkout (see assets/3dhop/NOTICE.md); re-clone the repository rather than editing "
            "around this, the viewer is a committed source, not generated"
        )

    entries = collect_bundle_entries(out_dir)
    model_count = sum(1 for arcname, _ in entries if arcname.startswith("data/model/"))
    texture_count = sum(1 for arcname, _ in entries if arcname.startswith("data/textures/"))

    zip_path = DIST / f"{slug}.zip"
    # Idempotency: drop a stale ZIP from a previous run first, same
    # reasoning as step_nexus.py clearing its own two output files --
    # write_deterministic_zip() always writes every entry fresh anyway, but
    # an explicit unlink means a failed/partial run never leaves a stale
    # ZIP looking like a successful one.
    zip_path.unlink(missing_ok=True)
    write_deterministic_zip(entries, zip_path)

    size = zip_path.stat().st_size
    message = (
        f"bundled {slug} -> {zip_path.relative_to(DIST.parent)} "
        f"({model_count} model file(s), {texture_count} texture(s), "
        f"{len(viewer_files)} viewer file(s), {size:,} bytes)"
    )
    return True, message


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", help="Which model (dist/<slug>/) to bundle. Auto-detected if exactly one exists.")
    ok, message = run(ap.parse_args())
    print(f"[bundle] {message}")
    raise SystemExit(0 if ok else 1)
