"""Shared constants, paths and canonical writers for fdo-3d-packager.

Import this from every step module rather than re-deriving RELEASE, the path
layout or JSON writing conventions three different ways. See PRIMER.md A3 for
the rules this module exists to enforce.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

# No datetime.now() anywhere in this repo's generators (PRIMER.md A3). Bump
# this by hand when the pipeline output is meant to change.
RELEASE = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DIST = REPO_ROOT / "dist"

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


def load_source_info() -> dict:
    """Read data/raw/source_info.json, the S2 -> S3/S4/S5 handoff contract
    (see step_fetch.py:build_source_info -- slug/model_file/title/creator/
    licence/... plus todo_placeholders). Shared here rather than re-derived
    per step, per this module's own purpose (see docstring)."""
    path = DATA_RAW / "source_info.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run `python main.py --only fetch ...` first"
        )
    return read_json(path)


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
