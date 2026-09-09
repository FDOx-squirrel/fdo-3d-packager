"""build_fdo -- run dist/<slug>.zip through a local fdo-squirrel instance;
fdo-metadata.ttl is the proof the package is actually usable.

Mirrors fdo-squirrel-registry's own S8 ("Registry als FDO, Release und CI"):
"Der Bundle plus Index plus Shapes werden als ZIP durch fdo-squirrel
geschickt [...] der Rundlauf ist zugleich der beste Integrationstest." Same
principle here -- instead of reimplementing RDF generation, this step feeds
`bundle`'s (S6) freshly-built dist/<slug>.zip through fdo-squirrel's own
ingest and takes the resulting fdo-metadata.ttl as proof, not just a
schema-valid MD.cff. Unlike the registry, this repo's bundle ZIP is already
in fdo-squirrel's expected layout end to end -- no separate staging ZIP
needed here, dist/<slug>.zip goes in as-is.

**How fdo-squirrel is wired in (PRIMER.md Teil D, resolved 2026-09-07):**
pip dependency (requirements.txt, pinned commit -- same reasoning as the
vendored MD.cff-schema.yaml pin, PRIMER.md A4 "Gepinnte Laufzeit"), invoked
as the console script installed next to this interpreter -- copied from
fdo-squirrel-registry's step_release.py (PRIMER.md A3: reuse means copying,
not referencing), see `_fdo_squirrel_executable()` below for why neither
$PATH nor `-m main` work here (this repo's own orchestrator is also
`main.py`, same collision registry hit).

Offline in the PRIMER.md A3 sense that matters here: no network call of its
own (fdo-squirrel reads the local dist/<slug>.zip, does not re-fetch
anything) -- unlike `fetch`, this step's `network=False` in main.py's STEPS
table is correct even though it shells out to another program.

**Real finding from this step's own first real run (govan-2.zip,
freshford-st-lachtains-well-low-poly.zip, both already committed in dist/
from S6's real run at Flo's):** fdo-squirrel does NOT abort and does NOT
ignore unclassified files -- `fdo/classification_rules.yaml` falls back to
role "data" for anything it has no rule for. Confirmed, not just the
suspected gap from S6:
  - `data/model/model.mtl` -> "data" (no `.mtl` rule at all)
  - `data/textures/*.jpeg` -> "documentation", not "auxiliary" -- the
    existing `textures/` rule is a path-PREFIX match, so it only ever
    matched a top-level `textures/`, never this bundle's `data/textures/`
  - `viewer/*.html`/`.js`/`.css` -> "data" (no rule for any of the three)
No pipeline failure either way -- fdo-metadata.ttl still comes out valid,
just with those distributions under the generic fallback role instead of
their real one. PRIMER.md A4 already decided fixes for this belong in
fdo-squirrel's classification_rules.yaml, not worked around here by
pre-populating distributions[] ourselves -- that upstream patch is a
separate fdo-squirrel-repo chat, not part of this one (PRIMER.md A5: one
repo per chat). This step's own job is the round trip and the finding, not
the fix.

**Fixed upstream (fdo-squirrel S18-S20, commit `e538366`, pin bumped
2026-09-09):** confirmed against the same three cases, now correct --
`data/model/model.mtl` -> "model", `data/textures/*.jpeg` -> "auxiliary",
`viewer/*` -> "auxiliary". Same commit also drops the `creators[].id`
hard-requirement (see `step_mdcff.py`) and stops writing JPG diagrams
alongside the PNG/SVG ones (nothing to change on this repo's side for
either, both were entirely fdo-squirrel's own behaviour). See PRIMER.md
Teil A4 for the pin-bump entry and Teil D for the now-closed items.

Completeness gate: dist/<slug>.zip must already exist (`bundle`, S6, must
have run). `--slug` picks which one -- resolved against dist/<slug>.zip
itself (`fdo_3d_packager_utils.py:resolve_bundle_slug()`), deliberately
*not* the data/raw/<slug>/-based `resolve_slug()` that S3-S6 use: this
step's real first run (see below) found dist/govan-2.zip and
dist/freshford-st-lachtains-well-low-poly.zip already committed in this
repo *without* their data/raw/ counterpart, and this step has no actual
need for data/raw/ to still exist -- the bundle ZIP is self-contained.

Output goes to dist/<slug>_release/ (fdo-metadata.ttl, the HTML modelling
report, the Mermaid source, and fdo-squirrel's own re-zipped
"finished FDO bundle") -- gitignored, same reasoning as
fdo-squirrel-registry's dist/release/: a rebuildable byproduct of an
already-committed source (dist/<slug>.zip itself), not a second citable
fassung. Zenodo publishing stays a manual step for a human with
credentials, same as `fetch`'s network exclusion (PRIMER.md A3) and
registry's own S8.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Optional

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import DIST, resolve_bundle_slug


def _fdo_squirrel_executable() -> Optional[Path]:
    """The fdo-squirrel console script installed in *this* interpreter's
    environment, found the way pip actually put it there.

    Copied from fdo-squirrel-registry's py/step_release.py (PRIMER.md A3:
    reuse means copying, not referencing) -- same three reasons apply here
    unchanged:

    Not `shutil.which("fdo-squirrel")`: that walks $PATH, which does not
    include a venv's scripts directory unless the venv was activated -- true
    even when fdo-squirrel is correctly installed in the exact environment
    running this script. Not `sys.executable -m main` either: fdo-squirrel's
    entry module is named `main`, and Python puts the current directory
    first on a subprocess's sys.path for `-m` -- since this repository's own
    orchestrator is also `main.py`, that resolves to *this* repo's file, not
    fdo-squirrel's, the moment this step runs from the repository root,
    which is exactly the case here.

    Not `Path(sys.executable).parent / "fdo-squirrel"` either, on its own:
    right for a POSIX venv and a Windows venv (script and interpreter are
    siblings in both), but wrong for a plain, non-venv Windows install,
    where `python.exe` sits at the installation root while pip puts console
    scripts in a `Scripts\\` subdirectory next to it, not beside it.
    `sysconfig.get_path("scripts")` is what pip itself consults to decide
    where a console script goes, so it is correct in all three layouts;
    kept as the first candidate, with the sibling-of-python.exe path second
    as a fallback for anything unusual enough to disagree with it.
    """
    name = "fdo-squirrel.exe" if sys.platform == "win32" else "fdo-squirrel"
    candidates = [
        Path(sysconfig.get_path("scripts")) / name,
        Path(sys.executable).parent / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run(args: argparse.Namespace) -> tuple[bool, str]:
    slug = resolve_bundle_slug(getattr(args, "slug", None))
    zip_path = DIST / f"{slug}.zip"
    if not zip_path.exists():
        return False, f"{zip_path} not found -- run `python main.py --only bundle` first"

    exe = _fdo_squirrel_executable()
    if exe is None:
        return False, (
            "fdo-squirrel not installed in this interpreter's environment -- "
            "pip install -r requirements.txt"
        )

    release_dir = DIST / f"{slug}_release"
    # Idempotency: drop a stale release dir from a previous run first, same
    # reasoning as step_bundle.py's stale-ZIP unlink and step_nexus.py's
    # stale-output unlink -- fdo-squirrel writes several files directly into
    # --outdir, a leftover file from an earlier, differently-shaped run
    # should never masquerade as this run's output.
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True)

    # check=True: a failed fdo-squirrel run must stop the pipeline, not be
    # silently swallowed (PRIMER.md A3, same guard as the nxsbuild/
    # nxscompress/Blender subprocess calls in step_nexus.py/step_convert.py).
    # Output streams straight through, same as those two -- not captured,
    # for the same reason: this repo's own convention, not registry's.
    subprocess.run([str(exe), "--package", str(zip_path), "--outdir", str(release_dir)], check=True)

    ttl_path = release_dir / "fdo-metadata.ttl"
    if not ttl_path.exists():
        return False, f"fdo-squirrel ran but did not produce {ttl_path}"

    bundle_path = next(release_dir.glob("*-fdo-bundle.zip"), None)
    message = (
        f"{slug} -> {ttl_path.relative_to(DIST.parent)} ({ttl_path.stat().st_size:,} bytes) "
        f"-- fdo-squirrel round-trip confirmed"
        + (f", finished bundle in {release_dir.relative_to(DIST.parent)} (not published, "
           "Zenodo needs a human with credentials)" if bundle_path else "")
    )
    return True, message


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", help="Which model (dist/<slug>.zip) to run through fdo-squirrel. Auto-detected if exactly one exists.")
    ok, message = run(ap.parse_args())
    print(f"[build_fdo] {message}")
    raise SystemExit(0 if ok else 1)
