"""mdcff -- write MD.cff + CITATION.cff, validate against fdo-squirrel's
MD.cff-schema.yaml.

Needs the descriptive metadata from `fetch` (title/creator/licence/source)
and requires `nexus` to have completed (checked below), so it runs after
both -- but does NOT read S4's checksums into MD.cff: `distributions[]` is
deliberately left out (PRIMER.md A4, decided 2026-09-03) since fdo-squirrel
classifies the package itself. `fdo_type` is fixed to "fdo:3DDataFDO"
(PRIMER.md A4).

Offline (PRIMER.md A3): validates against schemas/md_cff/MD.cff-schema.yaml,
a vendored copy of fdo-squirrel's schema (see that file's own header for
provenance/refresh instructions), not a live fetch.

Decisions confirmed in this step (PRIMER.md S5, see PRIMER.md for the dated
A4 rows):
- `description` (schema-required): if `fetch` didn't supply one (Sketchfab
  metadata empty, or --local which has no --description flag at all), this
  step writes a deterministic fallback sentence from title/creator rather
  than adding a new fetch-time TODO field. Silent, not a Warning -- that is
  the point of choosing a fallback over another CLI-gated placeholder.
- `publishers` (schema-required): no default (e.g. no silent LEIZA
  fallback). `--publisher-label` is mandatory for this step; missing it is
  a hard failure (return False), same tier as a missing nxsbuild binary in
  step_nexus.py -- not folded into the soft-Warning/--strict mechanism
  below, because unlike title/creator/licence there is no sensible
  placeholder value that still describes *who* is publishing.
- `source_info.json`'s own `todo_placeholders` (title/creator/licence
  missing at fetch time) stay a soft Warning here, exactly like fetch's own
  pattern: `python main.py` still succeeds, `--strict` (CI) fails. This
  confirms the "Vorschlag" PRIMER.md A4 had flagged for this step.
- `id` (schema-required, global identifier): always a fixed placeholder
  string, deliberately outside the Warning/--strict mechanism above --
  PRIMER.md A4 already decided this repo never assigns a PID, so unlike the
  above this is not a fixable-before-release gap and must not fail --strict
  CI runs that will never have a DOI to give it.
- `keywords`: a small fixed default (3D data / Cultural Heritage, matching
  fdo-squirrel's own root MD.cff Wikidata IDs) rather than CLI-configurable
  -- this whole repo's output is always in that category.
- CITATION.cff `authors`: written as a CFF *entity* ({name, website}), not
  a *person* ({given-names, family-names}) -- source_info's `creator` is an
  arbitrary display string (Sketchfab username, or free text for --local)
  that cannot be reliably split into given/family names.
- CITATION.cff `license`: only written if the licence string looks like a
  plausible SPDX identifier (CFF's `license` key is SPDX-only, unlike
  MD.cff's free-text `license.label`); source_info's `licence` is often a
  human-readable label (e.g. Sketchfab's "CC Attribution"), not guaranteed
  SPDX-valid, so this is a best-effort heuristic, not a validator.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from jsonschema import Draft202012Validator

from py.fdo_3d_packager_utils import DIST, REPO_ROOT, load_source_info, write_yaml

SCHEMA_PATH = REPO_ROOT / "schemas" / "md_cff" / "MD.cff-schema.yaml"

# PRIMER.md A4 (2026-09-03): this repo never mints a PID. `MD.cff.id` stays
# this fixed placeholder until a manual Zenodo upload gives it a real DOI --
# see this module's own docstring for why that is NOT folded into the
# Warning/--strict mechanism below.
ID_PLACEHOLDER = "TODO: id not set (pending Zenodo DOI, see PRIMER.md A4)"

# PRIMER.md S5 (this step): fixed default, matches fdo-squirrel's own root
# MD.cff Wikidata IDs for the same concepts -- see module docstring.
DEFAULT_KEYWORDS = [
    {"label": "3D data", "id": "http://www.wikidata.org/entity/Q229370"},
    {"label": "Cultural Heritage", "id": "http://www.wikidata.org/entity/Q110840"},
]

# Loose heuristic for "looks like an SPDX license identifier" (CITATION.cff
# `license` key only, see module docstring) -- not a real SPDX list lookup,
# just enough to reject obviously-human labels like "CC Attribution" or a
# "TODO: ..." placeholder.
_SPDX_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[.+-][A-Za-z0-9]+)*$")


def _looks_like_spdx(value: str) -> bool:
    return bool(_SPDX_LIKE_RE.match(value)) and not value.upper().startswith("TODO")


def _entity(label: str, entity_id: str | None) -> dict:
    """{label, id?} per MD.cff-schema.yaml's idLabelEntityOptionalId --
    omit `id` entirely rather than writing it as null (additionalProperties
    is false but a null id would still be a *type* violation, not just
    noise)."""
    out = {"label": label}
    if entity_id:
        out["id"] = entity_id
    return out


def build_description(info: dict) -> str:
    description = (info.get("description") or "").strip()
    if description:
        return description
    return (
        f"3D dataset \u2018{info['title']}\u2019, digitised by {info['creator']}. "
        "Packaged as a FAIR Digital Object (fdo:3DDataFDO) with fdo-3d-packager."
    )


def build_md_cff(info: dict, publisher_label: str, publisher_id: str | None) -> dict:
    md_cff: dict = {
        "md_cff_version": "0.1",
        "fdo_type": "fdo:3DDataFDO",
        "id": ID_PLACEHOLDER,
        "title": info["title"],
        "description": build_description(info),
        "publishers": [_entity(publisher_label, publisher_id)],
        "creators": [_entity(info["creator"], info.get("creator_profile"))],
        "license": _entity(info["licence"], info.get("licence_url")),
        "keywords": [dict(k) for k in DEFAULT_KEYWORDS],
    }
    source_url = info.get("source_url")
    if source_url:
        md_cff["related_resources"] = [{
            "relation": "isDerivedFrom",
            "target": _entity(f"Source: {info['title']}", source_url),
        }]
    return md_cff


def build_citation_cff(info: dict) -> dict:
    author: dict = {"name": info["creator"]}
    if info.get("creator_profile"):
        author["website"] = info["creator_profile"]

    citation: dict = {
        "cff-version": "1.2.0",
        "message": "If you use this dataset, please cite it using the metadata from this file.",
        "title": info["title"],
        "type": "dataset",
        "authors": [author],
    }
    licence = info.get("licence") or ""
    if _looks_like_spdx(licence):
        citation["license"] = licence
    if info.get("source_url"):
        citation["url"] = info["source_url"]
    return citation


def validate_md_cff(md_cff: dict) -> list[str]:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(md_cff), key=lambda e: list(e.path))
    return [
        (("$." + ".".join(str(p) for p in e.path)) if e.path else "$") + f": {e.message}"
        for e in errors
    ]


def run(args: argparse.Namespace) -> tuple[bool, str]:
    info = load_source_info()
    slug = info["slug"]
    out_dir = DIST / slug

    # Completeness gate: nexus (S4) must have run, even though its
    # checksums don't end up in MD.cff (module docstring) -- a package
    # description written before the artefacts it describes exist would be
    # a description of nothing.
    for required_name in ("model.obj", "model.nxs", "model.nxz"):
        if not (out_dir / required_name).exists():
            return False, (
                f"{out_dir / required_name} not found -- run "
                "`python main.py --only convert` and `--only nexus` first"
            )

    publisher_label = getattr(args, "publisher_label", None)
    if not publisher_label:
        return False, (
            "publisher label required: pass --publisher-label "
            "(+ optional --publisher-id), no default (PRIMER.md A4)"
        )
    publisher_id = getattr(args, "publisher_id", None)

    md_cff = build_md_cff(info, publisher_label, publisher_id)
    schema_errors = validate_md_cff(md_cff)
    if schema_errors:
        # A schema-invalid MD.cff coming out of this function is a bug in
        # this step, not a data-quality issue -- fail hard either way.
        return False, "generated MD.cff failed schema validation:\n" + "\n".join(schema_errors)

    citation_cff = build_citation_cff(info)

    write_yaml(md_cff, out_dir / "MD.cff")
    write_yaml(citation_cff, out_dir / "CITATION.cff")

    message = f"wrote {slug} -> MD.cff, CITATION.cff"
    if info["todo_placeholders"]:
        message = (
            "Warning: " + message + " -- source_info.json has unresolved "
            f"TODO placeholder(s): {', '.join(info['todo_placeholders'])} "
            "(fix via `--only fetch` with --title/--creator/--licence, or "
            "edit data/raw/source_info.json by hand)"
        )
    return True, message


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publisher-label", help="MD.cff publishers[0].label. Required, no default (PRIMER.md A4).")
    ap.add_argument("--publisher-id", help="MD.cff publishers[0].id, e.g. a ROR URL. Optional.")
    ok, message = run(ap.parse_args())
    print(f"[mdcff] {message}")
    raise SystemExit(0 if ok else 1)
