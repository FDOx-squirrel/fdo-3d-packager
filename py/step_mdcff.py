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

Decisions confirmed 2026-09-07 (PRIMER.md S5, see PRIMER.md for the dated
A4 rows -- kept short here, the "why" lives there, not duplicated per line):
- `description`: deterministic fallback sentence from title/creator if
  `fetch` didn't supply one, silent (no Warning).
- `publishers`: no hardcoded default. `--publisher-label` falls back to the
  `FDO_PUBLISHER_LABEL` environment variable (same pattern as
  `--blender-bin`/`BLENDER_BIN`); still hard-fails if neither is set --
  this repo's actual publisher is "Research Squirrel Engineers Network",
  essentially never LEIZA, since almost every model packaged here belongs
  to an external creator (citizen scientists, museums) or is Flo's own
  private work -- LEIZA has no institutional claim to publish it.
- `source_info.json`'s own `todo_placeholders` stay a soft Warning here
  (confirms the PRIMER.md A4 2026-09-04 proposal).
- `id`: always a fixed placeholder, outside the Warning/--strict mechanism.
- `keywords`: fixed defaults (3D data / Cultural Heritage) merged with
  Sketchfab tags/categories when available (see `load_sketchfab_meta()`).
- CITATION.cff `authors`: CFF *entity* ({name, website}), not *person*.
- CITATION.cff/MD.cff `license`: Sketchfab's `license.slug` (e.g. "cc-by")
  is mapped to a real SPDX id via `SKETCHFAB_LICENSE_SLUG_TO_SPDX` when
  available -- far more reliable than guessing from the human label, which
  is all a `--local` run ever has, where the old heuristic still applies.

`load_sketchfab_meta()` reads `data/raw/<slug>/sketchfab_meta.json` -- the
full raw Data API v3 response `fetch` (S2) already stashes for every
`--sketchfab` run, previously write-only (audit trail only). This step is
the first to actually read it back, pulling in whatever `source_info.json`
doesn't carry: tags, categories, `license.slug`, `publishedAt`/`createdAt`,
the canonical `viewerUrl`, `faceCount`/`vertexCount`. Absent for `--local`
runs (no such file) or if fetch predates this step -- every field below is
optional and MD.cff/CITATION.cff still build without it, just leaner.

`--slug` (see `fdo_3d_packager_utils.py`:`resolve_slug()`) picks which
fetched model to describe when more than one exists under `data/raw/`;
auto-detected when exactly one does. `main.py --all-slugs` loops this step
(and any others selected) over every one of them.
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

from py.fdo_3d_packager_utils import DATA_RAW, DIST, REPO_ROOT, load_source_info, read_json, write_yaml

SCHEMA_PATH = REPO_ROOT / "schemas" / "md_cff" / "MD.cff-schema.yaml"

# PRIMER.md A4 (2026-09-03): this repo never mints a PID. `MD.cff.id` stays
# this fixed placeholder until a manual Zenodo upload gives it a real DOI --
# see this module's own docstring for why that is NOT folded into the
# Warning/--strict mechanism below.
ID_PLACEHOLDER = "TODO: id not set (pending Zenodo DOI, see PRIMER.md A4)"

# PRIMER.md S5 (this step): fixed baseline, matches fdo-squirrel's own root
# MD.cff Wikidata IDs for the same concepts -- see module docstring.
DEFAULT_KEYWORDS = [
    {"label": "3D data", "id": "http://www.wikidata.org/entity/Q229370"},
    {"label": "Cultural Heritage", "id": "http://www.wikidata.org/entity/Q110840"},
]

# Corrected 2026-09-07 (5) against a real Data API v3 response (Govan 2,
# uploaded in this chat): Sketchfab's license.slug for "CC Attribution" is
# "by", NOT "cc-by" -- the earlier version of this dict used "cc-by" etc.,
# reconstructed from an unofficial third-party OpenAPI/JSON-Schema profile
# (api-evangelist/sketchfab) that turned out to have invented the wrong
# slug format. It would never have matched a single real Sketchfab
# response. Kept only as a fallback now -- see _spdx_from_license_url()
# below, which parses the CC license URL (already in source_info.json's
# licence_url for every real --sketchfab run, and standard enough to work
# for --local too) instead of relying on a Sketchfab-specific slug at all.
# "st" (paid "Standard" license) and "ed" ("Editorial", not freely
# reusable) have no SPDX equivalent and are deliberately absent.
SKETCHFAB_LICENSE_SLUG_TO_SPDX = {
    "by": "CC-BY-4.0",
    "by-sa": "CC-BY-SA-4.0",
    "by-nd": "CC-BY-ND-4.0",
    "by-nc": "CC-BY-NC-4.0",
    "by-nc-sa": "CC-BY-NC-SA-4.0",
    "by-nc-nd": "CC-BY-NC-ND-4.0",
    "cc0": "CC0-1.0",
}

# Loose fallback heuristic for "looks like an SPDX license identifier"
# (last resort after _spdx_from_license_url() and
# SKETCHFAB_LICENSE_SLUG_TO_SPDX both come up empty, i.e. non-CC --local
# licences) -- not a real SPDX list lookup, just enough to reject
# obviously-human labels like "CC Attribution" or a "TODO: ..." placeholder.
_SPDX_LIKE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[.+-][A-Za-z0-9]+)*$")

# creativecommons.org URL -> SPDX id. The SPDX segment names (BY, BY-SA,
# BY-NC-ND, ...) are literally the same words the CC URL path uses, so
# this is a general-purpose, Sketchfab-independent derivation -- works for
# any licence_url that follows the standard CC URL shape, --sketchfab or
# --local. Primary source for CITATION.cff's `license`, added 2026-09-07
# (5) after the slug-based approach above was found wrong against real
# data (see SKETCHFAB_LICENSE_SLUG_TO_SPDX's comment).
_CC_LICENSE_URL_RE = re.compile(
    r"creativecommons\.org/licenses/([a-z]+(?:-[a-z]+)*)/(\d+\.\d+)", re.IGNORECASE
)
_CC0_URL_RE = re.compile(
    r"creativecommons\.org/publicdomain/zero/(\d+\.\d+)", re.IGNORECASE
)

# First 10 characters of an ISO-8601 timestamp, if they look like a date --
# Sketchfab's publishedAt/createdAt come as full timestamps
# ("2026-03-15T10:22:31.123456Z"), MD.cff/CFF dates want just YYYY-MM-DD.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _looks_like_spdx(value: str) -> bool:
    return bool(_SPDX_LIKE_RE.match(value)) and not value.upper().startswith("TODO")


def _spdx_from_license_url(url: str | None) -> str | None:
    """CC licence URL -> SPDX id, e.g.
    "http://creativecommons.org/licenses/by/4.0/" -> "CC-BY-4.0",
    ".../publicdomain/zero/1.0/" -> "CC0-1.0". None for anything that
    isn't a recognisable creativecommons.org URL (not an error -- plenty
    of valid licence_url values aren't CC at all)."""
    if not url:
        return None
    zero_match = _CC0_URL_RE.search(url)
    if zero_match:
        return f"CC0-{zero_match.group(1)}"
    match = _CC_LICENSE_URL_RE.search(url)
    if match:
        return f"CC-{match.group(1).upper()}-{match.group(2)}"
    return None


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    match = _ISO_DATE_RE.match(value)
    return match.group(0) if match else None


def _entity(label: str, entity_id: str | None) -> dict:
    """{label, id?} per MD.cff-schema.yaml's idLabelEntityOptionalId --
    omit `id` entirely rather than writing it as null (additionalProperties
    is false but a null id would still be a *type* violation, not just
    noise)."""
    out = {"label": label}
    if entity_id:
        out["id"] = entity_id
    return out


def load_sketchfab_meta(info: dict) -> dict | None:
    """The raw Sketchfab Data API v3 response `fetch` (S2) already saved to
    data/raw/<slug>/sketchfab_meta.json for `--sketchfab` runs (audit trail
    -- see step_fetch.py:_fetch_one_sketchfab). Returns None for `--local`
    runs (no such file) or if it's missing/unreadable for any other reason
    -- every caller treats this as optional enrichment, never a
    requirement."""
    if info.get("input_mode") != "sketchfab":
        return None
    path = DATA_RAW / info["slug"] / "sketchfab_meta.json"
    if not path.exists():
        return None
    try:
        return read_json(path)
    except (ValueError, OSError):
        return None


def extract_enrichment(meta: dict | None) -> dict:
    """Pulls the fields MD.cff/CITATION.cff can use out of a raw Sketchfab
    model response that source_info.json doesn't already carry: tags,
    categories, license slug, dates, canonical viewer URL, mesh stats.
    Every key is optional in the return value -- callers use `.get()`."""
    if not meta:
        return {}

    tags = [t.get("name") for t in (meta.get("tags") or []) if t.get("name")]
    categories = [c.get("name") for c in (meta.get("categories") or []) if c.get("name")]
    license_info = meta.get("license") or {}

    out: dict = {}
    if tags or categories:
        # Case-insensitive de-dup, first-seen order, tags before categories.
        seen: set[str] = set()
        merged = []
        for label in tags + categories:
            key = label.strip().lower()
            if key and key not in seen:
                seen.add(key)
                merged.append(label.strip())
        out["keyword_labels"] = merged
    if license_info.get("slug"):
        out["license_slug"] = license_info["slug"]
    if _iso_date(meta.get("publishedAt")):
        out["date_released"] = _iso_date(meta.get("publishedAt"))
    if _iso_date(meta.get("createdAt")):
        out["date_created"] = _iso_date(meta.get("createdAt"))
    if meta.get("viewerUrl"):
        out["viewer_url"] = meta["viewerUrl"]
    if isinstance(meta.get("faceCount"), int) and isinstance(meta.get("vertexCount"), int):
        out["face_count"] = meta["faceCount"]
        out["vertex_count"] = meta["vertexCount"]
    return out


def build_description(info: dict) -> str:
    description = (info.get("description") or "").strip()
    if description:
        return description
    return (
        f"3D dataset \u2018{info['title']}\u2019, digitised by {info['creator']}. "
        "Packaged as a FAIR Digital Object (fdo:3DDataFDO) with fdo-3d-packager."
    )


def build_technique(info: dict, enrichment: dict) -> dict | None:
    """Optional MD.cff `technique` block: `--local`'s free-text
    `--source-note` (acquisition method, e.g. "KiriEngine, 180 photos,
    2026-03") as `acquisition.method`, and/or a processing note built from
    Sketchfab's mesh stats. Returns None (key omitted entirely) if neither
    is available -- an empty `technique: {}` would be noise, not data."""
    technique: dict = {}
    source_note = info.get("source_note")
    if source_note:
        technique["acquisition"] = {"method": source_note}
    if "face_count" in enrichment:
        technique["processing"] = (
            f"Sketchfab upload: {enrichment['face_count']:,} faces, "
            f"{enrichment['vertex_count']:,} vertices."
        )
    return technique or None


def build_md_cff(info: dict, enrichment: dict, publisher_label: str, publisher_id: str | None) -> dict:
    md_cff: dict = {
        "md_cff_version": "0.1",
        "fdo_type": "fdo:3DDataFDO",
        "id": ID_PLACEHOLDER,
        "title": info["title"],
        "description": build_description(info),
        "publishers": [_entity(publisher_label, publisher_id)],
        "creators": [_entity(info["creator"], info.get("creator_profile"))],
        "license": _entity(info["licence"], info.get("licence_url")),
    }
    if enrichment.get("date_created"):
        md_cff["date_created"] = enrichment["date_created"]
    if enrichment.get("date_released"):
        md_cff["date_released"] = enrichment["date_released"]

    keywords = [dict(k) for k in DEFAULT_KEYWORDS]
    seen = {k["label"].lower() for k in keywords}
    for label in enrichment.get("keyword_labels", []):
        if label.lower() not in seen:
            seen.add(label.lower())
            keywords.append({"label": label})
    md_cff["keywords"] = keywords

    source_url = enrichment.get("viewer_url") or info.get("source_url")
    if source_url:
        md_cff["related_resources"] = [{
            "relation": "isDerivedFrom",
            "target": _entity(f"Source: {info['title']}", source_url),
        }]

    technique = build_technique(info, enrichment)
    if technique:
        md_cff["technique"] = technique

    return md_cff


def build_citation_cff(info: dict, enrichment: dict) -> dict:
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

    spdx = (
        _spdx_from_license_url(info.get("licence_url"))
        or SKETCHFAB_LICENSE_SLUG_TO_SPDX.get(enrichment.get("license_slug", ""))
    )
    if not spdx and _looks_like_spdx(info.get("licence") or ""):
        spdx = info["licence"]
    if spdx:
        citation["license"] = spdx

    if enrichment.get("date_released"):
        citation["date-released"] = enrichment["date_released"]

    keywords = enrichment.get("keyword_labels")
    if keywords:
        citation["keywords"] = list(keywords)

    source_url = enrichment.get("viewer_url") or info.get("source_url")
    if source_url:
        citation["url"] = source_url

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
    info = load_source_info(getattr(args, "slug", None))
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
            "publisher label required: pass --publisher-label, or set the "
            "FDO_PUBLISHER_LABEL environment variable (+ optional "
            "--publisher-id / FDO_PUBLISHER_ID) -- no hardcoded default "
            "(PRIMER.md A4)"
        )
    publisher_id = getattr(args, "publisher_id", None)

    enrichment = extract_enrichment(load_sketchfab_meta(info))

    md_cff = build_md_cff(info, enrichment, publisher_label, publisher_id)
    schema_errors = validate_md_cff(md_cff)
    if schema_errors:
        # A schema-invalid MD.cff coming out of this function is a bug in
        # this step, not a data-quality issue -- fail hard either way.
        return False, "generated MD.cff failed schema validation:\n" + "\n".join(schema_errors)

    citation_cff = build_citation_cff(info, enrichment)

    write_yaml(md_cff, out_dir / "MD.cff")
    write_yaml(citation_cff, out_dir / "CITATION.cff")

    message = f"wrote {slug} -> MD.cff, CITATION.cff"
    if enrichment:
        message += f" (enriched from sketchfab_meta.json: {', '.join(sorted(enrichment))})"
    if info["todo_placeholders"]:
        message = (
            "Warning: " + message + " -- source_info.json has unresolved "
            f"TODO placeholder(s): {', '.join(info['todo_placeholders'])} "
            "(fix via `--only fetch` with --title/--creator/--licence, or "
            "edit data/raw/source_info.json by hand)"
        )
    return True, message


if __name__ == "__main__":
    import os

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publisher-label", default=os.environ.get("FDO_PUBLISHER_LABEL"),
                     help="MD.cff publishers[0].label. Required (or set FDO_PUBLISHER_LABEL), no hardcoded default (PRIMER.md A4).")
    ap.add_argument("--publisher-id", default=os.environ.get("FDO_PUBLISHER_ID"),
                     help="MD.cff publishers[0].id, e.g. a GitHub/ROR URL. Optional (or set FDO_PUBLISHER_ID).")
    ap.add_argument("--slug", help="Which fetched model (data/raw/<slug>/) to describe. Auto-detected if exactly one exists.")
    ok, message = run(ap.parse_args())
    print(f"[mdcff] {message}")
    raise SystemExit(0 if ok else 1)
