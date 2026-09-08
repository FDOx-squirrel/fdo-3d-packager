"""Shared constants, paths and canonical writers for fdo-3d-packager.

Import this from every step module rather than re-deriving RELEASE, the path
layout or JSON writing conventions three different ways. See PRIMER.md A3 for
the rules this module exists to enforce.
"""
from __future__ import annotations

import hashlib
import json
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

# Curated MD.cff/CITATION.cff field overrides (PRIMER.md S10) -- Flo's own
# research (Wikidata object type, OSM spatial id, ChronOntology period,
# condition assessment, ...) that `mdcff` (S5) has no way to derive itself.
# Like DATA_RAW, this is real hand-authored data, never a repo artefact --
# covered by the existing `data/*` line in .gitignore, no separate entry
# needed. Unlike DATA_RAW, nothing in this repo ever creates it (the user
# writes data/local-metadata/<slug>/MD.cff by hand), so no ensure_dirs()
# entry for it either.
LOCAL_METADATA = REPO_ROOT / "data" / "local-metadata"

# Vendored, offline third-party assets (PRIMER.md A3: network access stays
# confined to `fetch`). Currently just the trimmed 3DHOP viewer the `bundle`
# step (S6) copies into every dist/<slug>.zip -- see assets/3dhop/NOTICE.md
# for what was vendored, from where, and why.
ASSETS = REPO_ROOT / "assets"
VIEWER_SRC = ASSETS / "3dhop"

# This repo does not publish RDF itself (that is fdo-squirrel's job
# downstream), so unlike other repos in the family there is no
# write_canonical_turtle() here -- see PRIMER.md A6.


def ensure_dirs() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)


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
    """Every slug a bundle currently exists for, i.e. dist/<slug>.zip --
    build_fdo (S7)'s own input. Deliberately independent of
    discover_slugs()/data/raw/ above: found the hard way (S7, real run
    against this repo's own committed dist/govan-2.zip and
    dist/freshford-st-lachtains-well-low-poly.zip) -- both ship without a
    data/raw/<slug>/ counterpart (not committed, see A5), so a slug
    resolution that goes through load_source_info() fails on exactly the
    real fixtures this step is meant to run against. The bundle ZIP is
    self-contained; S7 has no reason to require data/raw/ to still exist.
    Sorted for determinism, same reasoning as discover_slugs()."""
    if not DIST.exists():
        return []
    return sorted(p.stem for p in DIST.glob("*.zip"))


def resolve_bundle_slug(explicit: str | None) -> str:
    """--slug resolution for build_fdo (S7), mirroring resolve_slug() above
    but against dist/<slug>.zip (discover_bundle_slugs()) instead of
    data/raw/<slug>/ -- see that function's docstring for why the two
    cannot share one implementation."""
    if explicit:
        return explicit
    slugs = discover_bundle_slugs()
    if len(slugs) == 1:
        return slugs[0]
    if not slugs:
        raise FileNotFoundError(
            "no dist/<slug>.zip found -- run `python main.py --only bundle ...` first"
        )
    raise ValueError(
        f"multiple bundles found under dist/ ({', '.join(slugs)}) -- pass --slug to pick one, "
        "or --all-slugs to run every one of them"
    )


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
