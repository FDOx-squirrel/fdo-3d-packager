"""Shared constants, paths and canonical writers for fdo-3d-packager.

Import this from every step module rather than re-deriving RELEASE, the path
layout or JSON writing conventions three different ways. See PRIMER.md A3 for
the rules this module exists to enforce.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import yaml

# No datetime.now() anywhere in this repo's generators (PRIMER.md A3). Bump
# this by hand when the pipeline output is meant to change.
RELEASE = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DIST = REPO_ROOT / "dist"
# Intermediates (dist/_build/<slug>/ from convert/nexus/mdcff, and the bundle
# dist/_build/<slug>.zip) live apart from the finished result, so dist/ shows
# one dist/<slug>_release/ per model and nothing else (PRIMER.md S15).
BUILD = DIST / "_build"


def build_dir(slug: str) -> Path:
    """convert/nexus/mdcff output for one model: dist/_build/<slug>/."""
    return BUILD / slug


def bundle_zip(slug: str) -> Path:
    """The bundle step's output and build_fdo's input: dist/_build/<slug>.zip."""
    return BUILD / f"{slug}.zip"


def release_dir(slug: str) -> Path:
    """build_fdo's output: dist/<slug>_release/."""
    return DIST / f"{slug}_release"

# Curated MD.cff/CITATION.cff field overrides (PRIMER.md S10) -- Flo's own
# research (Wikidata object type, OSM spatial id, ChronOntology period,
# condition assessment, ...) that `mdcff` (S5) has no way to derive itself.
# Like DATA_RAW, this is real hand-authored data, never a repo artefact --
# covered by the existing `data/*` line in .gitignore, no separate entry
# needed. Unlike DATA_RAW, nothing in this repo ever creates it (the user
# writes data/local-metadata/<slug>/MD.cff by hand), so no ensure_dirs()
# entry for it either.
LOCAL_METADATA = REPO_ROOT / "data" / "local-metadata"

# Local, hand-supplied extra files (S12) -- e.g. SfM source photography, a
# raw camera-session folder, anything `bundle` (S6) has no way to derive
# and that should still travel inside the fdox package under `data/`.
# Same "never a repo artefact, no separate .gitignore entry" reasoning as
# LOCAL_METADATA above (data/* already covers it), but a different merge
# shape: LOCAL_METADATA overrides fixed, known filenames (MD.cff,
# CITATION.cff) field-by-field; this one mirrors whatever subfolder
# structure the user creates under data/local-data/<slug>/ straight into
# data/<...> in the bundle (S6/S12) -- the user decides that structure
# (e.g. one subfolder per SfM camera session), this repo doesn't
# interpret it, just copies it 1:1.
LOCAL_DATA = REPO_ROOT / "data" / "local-data"

# Vendored, offline third-party assets (PRIMER.md A3: network access stays
# confined to `fetch`). Currently just the trimmed 3DHOP viewer the `bundle`
# step (S6) copies into every dist/_build/<slug>.zip -- see assets/3dhop/NOTICE.md
# for what was vendored, from where, and why.
ASSETS = REPO_ROOT / "assets"
VIEWER_SRC = ASSETS / "3dhop"

# This repo does not publish RDF itself (that is fdo-squirrel's job
# downstream), so unlike other repos in the family there is no
# write_canonical_turtle() here -- see PRIMER.md A6.


def ensure_dirs() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)


def write_json(data: Any, path: Path) -> None:
    """Deterministic JSON: sorted keys, no ASCII escaping, trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_yaml(data: Any, path: Path) -> None:
    """Deterministic YAML for MD.cff/CITATION.cff (mdcff step, S5):
    insertion order preserved (sort_keys=False -- callers build dicts in the
    order they want to see on disk, matching each schema's own property
    order rather than alphabetical), block style, no line wrapping surprises
    on long URLs (width=1000), trailing newline. No datetime.now() involved
    here or in any caller (PRIMER.md A3)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True,
        default_flow_style=False, width=1000,
    )
    path.write_text(text, encoding="utf-8")


# zip format's own minimum timestamp. Used as a fixed per-entry date_time
# for every file `write_deterministic_zip()` writes -- not a meaningful
# content date (unlike RELEASE), just a placeholder that stops real file
# mtimes (which vary by OS/checkout/clone and carry no domain meaning here)
# from leaking into the archive and making two otherwise-identical runs
# diff (PRIMER.md A3: no clock in output).
ZIP_FIXED_DATETIME = (1980, 1, 1, 0, 0, 0)


def write_deterministic_zip(entries: list[tuple[str, Path]], zip_path: Path) -> None:
    """Write (arcname, source file) pairs into zip_path deterministically:
    fixed per-entry timestamp (ZIP_FIXED_DATETIME, see above) and fixed
    Unix file mode (0o644) instead of whatever the source file happened to
    have (differs by OS and by how the file was created), so two runs over
    unchanged inputs produce byte-identical output. `zipfile`'s default
    compression level (6) is itself deterministic for identical input
    bytes -- nothing to fix there. Entries are written in the exact order
    given; callers sort within each logical group themselves (filesystem
    iteration order isn't guaranteed across platforms, same reasoning as
    discover_slugs() below)."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, source in entries:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_FIXED_DATETIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, source.read_bytes())


def discover_slugs() -> list[str]:
    """Every slug fetch has produced so far -- every data/raw/<slug>/
    directory that has a source_info.json in it. Sorted for determinism
    (filesystem iteration order isn't guaranteed across platforms, and
    this repo's own rule is no unreproducible ordering anywhere, PRIMER.md
    A3). Shared by resolve_slug() below and by main.py's --all-slugs."""
    if not DATA_RAW.exists():
        return []
    return sorted(p.parent.name for p in DATA_RAW.glob("*/source_info.json"))


def resolve_slug(explicit: str | None) -> str:
    """--slug resolution shared by every per-slug step (convert/nexus/
    mdcff, S3-S5): an explicit --slug always wins; with none given, exactly
    one fetched slug can be inferred (today's single-model workflow keeps
    working unchanged), more than one requires --slug so a step never
    silently guesses which model it's about, and zero is the existing
    'run fetch first' situation (raised by load_source_info() itself, not
    here, so callers that want their own message can catch it)."""
    if explicit:
        return explicit
    slugs = discover_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if not slugs:
        raise FileNotFoundError(
            "no data/raw/<slug>/source_info.json found -- run `python main.py --only fetch ...` first"
        )
    raise ValueError(
        f"multiple slugs found under data/raw/ ({', '.join(slugs)}) -- pass --slug to pick one, "
        "or --all-slugs to run every one of them"
    )


def load_source_info(slug: str | None = None) -> dict:
    """Read data/raw/<slug>/source_info.json, the S2 -> S3/S4/S5 handoff
    contract (see step_fetch.py:build_source_info -- slug/model_file/title/
    creator/licence/... plus todo_placeholders). `slug` picks which fetched
    model; None auto-resolves via resolve_slug() (works unchanged for the
    common single-model case, requires --slug once more than one exists)."""
    resolved = resolve_slug(slug)
    path = DATA_RAW / resolved / "source_info.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run `python main.py --only fetch ...` first"
        )
    return read_json(path)


def discover_bundle_slugs() -> list[str]:
    """Every slug a bundle currently exists for, i.e. dist/_build/<slug>.zip --
    build_fdo (S7)'s own input. Deliberately independent of
    discover_slugs()/data/raw/ above: found the hard way (S7, real run
    against this repo's own committed dist/govan-2.zip and
    dist/freshford-st-lachtains-well-low-poly.zip) -- both ship without a
    data/raw/<slug>/ counterpart (not committed, see A5), so a slug
    resolution that goes through load_source_info() fails on exactly the
    real fixtures this step is meant to run against. The bundle ZIP is
    self-contained; S7 has no reason to require data/raw/ to still exist.
    Sorted for determinism, same reasoning as discover_slugs()."""
    if not BUILD.exists():
        return []
    return sorted(p.stem for p in BUILD.glob("*.zip"))


def resolve_bundle_slug(explicit: str | None) -> str:
    """--slug resolution for build_fdo (S7), mirroring resolve_slug() above
    but against dist/_build/<slug>.zip (discover_bundle_slugs()) instead of
    data/raw/<slug>/ -- see that function's docstring for why the two
    cannot share one implementation."""
    if explicit:
        return explicit
    slugs = discover_bundle_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if not slugs:
        legacy = sorted(DIST.glob("*.zip")) if DIST.exists() else []
        hint = (
            f" (found {len(legacy)} bundle(s) in the old layout directly under dist/ -- "
            "move them and their dist/<slug>/ folders into dist/_build/, see README)"
            if legacy else ""
        )
        raise FileNotFoundError(
            "no dist/_build/<slug>.zip found -- run `python main.py --only bundle ...` first"
            + hint
        )
    raise ValueError(
        f"multiple bundles found under dist/_build/ ({', '.join(slugs)}) -- pass --slug to pick one, "
        "or --all-slugs to run every one of them"
    )


def discover_release_slugs() -> list[str]:
    """Every slug a finished bundle exists for, i.e.
    dist/<slug>_release/<slug>-fdo-bundle.zip -- `validate` (S18)'s input.
    Independent of dist/_build/ on purpose: `--publish-only` (S11) deletes
    that folder and keeps only this bundle, and the bundle is what gets
    uploaded, so it is what should be checked. Sorted for determinism."""
    if not DIST.exists():
        return []
    return sorted(
        p.parent.name[: -len("_release")]
        for p in DIST.glob("*_release/*-fdo-bundle.zip")
        if p.name == f"{p.parent.name[: -len('_release')]}-fdo-bundle.zip"
    )


def resolve_release_slug(explicit: str | None) -> str:
    """--slug resolution for `validate`, mirroring resolve_bundle_slug()
    but against dist/<slug>_release/<slug>-fdo-bundle.zip."""
    if explicit:
        return explicit
    slugs = discover_release_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if not slugs:
        raise FileNotFoundError(
            "no dist/<slug>_release/<slug>-fdo-bundle.zip found -- run `python main.py --only build_fdo ...` first"
        )
    raise ValueError(
        f"multiple finished bundles found under dist/ ({', '.join(slugs)}) -- pass --slug to pick one, "
        "or --all-slugs to run every one of them"
    )


# --------------------------------------------------------------------------
# Child processes and the run log (PRIMER.md S19)
#
# Blender, nxsbuild and rocrate-validator write straight to the console, which
# a Python-level copy of sys.stdout (py/run_log.py) cannot see. So every
# child process goes through run_command(): without a run log it is exactly
# the old `subprocess.run(cmd, check=True)` (console output untouched), with
# one it is read line by line and printed through sys.stdout, so the log
# holds the same text the console shows.
# --------------------------------------------------------------------------

_CAPTURE_CHILD_OUTPUT = False


def set_capture_child_output(flag: bool) -> None:
    """Switched on by py/run_log.py while a run log is being written."""
    global _CAPTURE_CHILD_OUTPUT
    _CAPTURE_CHILD_OUTPUT = flag


def run_command(cmd: list[str], *, capture_env: dict[str, str] | None = None) -> None:
    """subprocess.run(cmd, check=True) that also feeds the run log.

    `capture_env` is merged into the child's environment only while a run
    log is active (e.g. a fixed terminal width and UTF-8 for the validator's
    boxed report, which would otherwise be 80 columns of cp1252 when piped);
    without a log the child inherits the console and the environment as
    before. Raises subprocess.CalledProcessError on a non-zero exit, like
    check=True."""
    if not _CAPTURE_CHILD_OUTPUT:
        subprocess.run(cmd, check=True)
        return
    env = dict(os.environ)
    env.update(capture_env or {})
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
    returncode = proc.wait()
    if returncode:
        raise subprocess.CalledProcessError(returncode, cmd)


def publish_only_cleanup(slug: str) -> list[str]:
    """--publish-only (S11): after a full run has confirmed the round trip
    through build_fdo, delete every intermediate this pipeline produced
    for `slug` except the one thing meant to actually leave the machine --
    dist/<slug>_release/<slug>-fdo-bundle.zip.

    Safe to do: that bundle is already self-contained (original package +
    every generated file -- fdo-squirrel's fdo_finalize.build_finished_
    bundle()) and therefore holds a copy of everything dist/_build/<slug>/,
    dist/_build/<slug>.zip and the rest of dist/<slug>_release/ (diagrams, TTL
    snippets, the HTML/JSON reports) still have -- confirmed by reading
    fdo-squirrel's own main.py: `generated_files` there is exactly the
    same list fdo-3d-packager writes into <slug>_release/, plus
    fdo-metadata.ttl and rdf_modelling_report.json, all folded into the
    bundle ZIP by name.

    Opt-in and only after a full run (see main.py's hook: this is called
    only when `build_fdo` was part of the selection that just succeeded)
    -- default runs keep every intermediate, because dist/_build/<slug>/ and
    dist/_build/<slug>.zip are exactly what the --from/--skip resumability
    contract (PRIMER.md A3) depends on existing between invocations. This
    is for a genuine "done, ship it" run, not the default.

    Returns the list of removed paths (relative to the repo root, sorted)
    so the caller can report what happened -- an empty list means there
    was nothing to remove (already clean, e.g. a repeated --publish-only
    call).
    """
    removed: list[str] = []

    raw_dir = build_dir(slug)
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
        removed.append(str(raw_dir.relative_to(REPO_ROOT)))

    zip_path = bundle_zip(slug)
    if zip_path.exists():
        zip_path.unlink()
        removed.append(str(zip_path.relative_to(REPO_ROOT)))

    # Leave no empty dist/_build/ behind once the last model is cleaned up.
    if BUILD.exists() and not any(BUILD.iterdir()):
        BUILD.rmdir()

    rel_dir = release_dir(slug)
    if rel_dir.exists():
        for p in rel_dir.iterdir():
            if p.name.endswith("-fdo-bundle.zip"):
                continue  # the one file --publish-only exists to keep
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(str(p.relative_to(REPO_ROOT)))

    return sorted(removed)


# Wavefront MTL texture-map directives whose last whitespace-separated token
# is a texture filename (options like -o/-s/-bm may precede it). Shared by
# step_fetch.py (S2, resolving --local .obj siblings) and step_convert.py
# (S3, moving Blender-exported textures into textures/ and rewriting these
# lines to point there).
MTL_TEXTURE_KEYS = (
    "map_Kd", "map_Ka", "map_Ks", "map_Ns", "map_d",
    "map_bump", "bump", "disp", "decal", "refl",
)


def content_fingerprint(path: Path) -> str:
    """SHA-256 hex digest of a file's bytes.

    Matches the `distributions[].sha256` convention in fdo-squirrel's
    MD.cff-schema.yaml (plain hex, no "sha256:" prefix there).
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nothing_to_do(reason: str = "not implemented yet (S1 skeleton)") -> tuple[bool, str]:
    """Standard S1 stub return value.

    Every step module returns this until its real implementation (S2+)
    lands. Keeps `python main.py` green and `--strict`-clean on a fresh
    checkout, per S1's Abnahme in PRIMER.md.
    """
    return True, f"nothing to do ({reason})"
