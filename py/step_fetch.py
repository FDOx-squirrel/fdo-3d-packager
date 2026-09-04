"""fetch -- resolve --sketchfab/--local into data/raw/.

The only step allowed to touch the network (Sketchfab Data/Download API).
Not part of the default `python main.py` run; call it explicitly:

    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/..."
    python main.py --only fetch --local ./scans/rathealy_kiriengine.glb --title "..." --creator "..." --licence "..."

S2: migrated from the sketchfab_fdo_prototype in the neighbouring chat --
Sketchfab Data API metadata harvest + Download API request for --sketchfab,
or a local-file copy/validate for --local. Writes exactly one model file to
data/raw/<slug>.<ext> plus data/raw/source_info.json (the S2/S3/S4/S5
handoff contract -- see build_source_info() docstring) and, for
--sketchfab, the raw API response to data/raw/sketchfab_meta.json for audit
(matches the prototype's convention).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import requests

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import DATA_RAW, ensure_dirs, write_json

SKETCHFAB_API = "https://api.sketchfab.com/v3"
UID_RE = re.compile(r"([0-9a-f]{32})")
MODEL_SUFFIXES = (".glb", ".gltf", ".obj")


# --------------------------------------------------------------------------
# Sketchfab path
# --------------------------------------------------------------------------

def extract_uid(url_or_uid: str) -> str:
    match = UID_RE.search(url_or_uid)
    if not match:
        raise ValueError(f"Could not extract a Sketchfab UID from '{url_or_uid}'")
    return match.group(1)


def guess_slug(url: str, uid: str) -> str:
    match = re.search(r"/3d-models/([a-z0-9-]+)-" + re.escape(uid), url)
    return match.group(1) if match else uid


def fetch_metadata(uid: str) -> dict:
    """Sketchfab Data API v3 -- public, no token needed."""
    r = requests.get(f"{SKETCHFAB_API}/models/{uid}", timeout=30)
    r.raise_for_status()
    return r.json()


def request_download_url(uid: str, token: str) -> str:
    """Sketchfab Download API -- needs a token, model must be marked
    downloadable by its owner. Link expires ~5 minutes after this call
    (Befund aus dem Prototyp-Chat), so download immediately."""
    headers = {"Authorization": f"Token {token}"}
    r = requests.get(f"{SKETCHFAB_API}/models/{uid}/download", headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "gltf" not in data:
        raise RuntimeError(f"No glTF archive in the download response: {json.dumps(data)}")
    return data["gltf"]["url"]


def download_file(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def unzip_archive(zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    return dest_dir


def find_model_file(root: Path) -> Path:
    for pattern in ("*.gltf", "*.glb"):
        hits = sorted(root.rglob(pattern))
        if hits:
            return hits[0]
    raise FileNotFoundError(f"No .gltf/.glb file found under {root}")


def build_source_info(
    *,
    input_mode: str,
    slug: str,
    model_file: str,
    title: str | None,
    description: str | None,
    creator: str | None,
    creator_profile: str | None,
    licence: str | None,
    licence_url: str | None,
    source_url: str | None,
    sketchfab_uid: str | None,
    source_note: str | None,
) -> dict:
    """The S2 -> S3/S4/S5 handoff contract.

    Every later step reads data/raw/source_info.json rather than
    re-deriving the slug or re-parsing CLI args: `model_file` tells
    `convert` (S3) which file under data/raw/ to feed to Blender, and
    title/creator/licence/source_url feed MD.cff + CITATION.cff (S5).
    `todo_placeholders` lists which required fields fell back to a
    "TODO: ..." placeholder because neither Sketchfab metadata nor a CLI
    flag supplied them -- S5 refuses to build MD.cff while this list is
    non-empty (Beschluss dieses Schritts, siehe PRIMER.md).
    """
    todos: list[str] = []

    def required(value: str | None, field: str) -> str:
        if value:
            return value
        todos.append(field)
        return f"TODO: {field} not set"

    return {
        "input_mode": input_mode,
        "slug": slug,
        "model_file": model_file,
        "title": required(title, "title"),
        "description": description,
        "creator": required(creator, "creator"),
        "creator_profile": creator_profile,
        "licence": required(licence, "licence"),
        "licence_url": licence_url,
        "source_url": source_url,
        "sketchfab_uid": sketchfab_uid,
        "source_note": source_note,
        "todo_placeholders": todos,
    }


def source_info_from_sketchfab(meta: dict, source_url: str, uid: str, args: argparse.Namespace) -> dict:
    license_info = meta.get("license") or {}
    user = meta.get("user") or {}
    username = user.get("username")
    return build_source_info(
        input_mode="sketchfab",
        slug=guess_slug(source_url, uid),
        model_file="",  # filled in by run() once the model file is copied
        title=args.title or meta.get("name"),
        description=meta.get("description"),
        creator=args.creator or user.get("displayName") or username,
        creator_profile=args.creator_profile or (f"https://sketchfab.com/{username}" if username else None),
        licence=args.licence or license_info.get("label") or license_info.get("slug"),
        licence_url=args.licence_url or license_info.get("url"),
        source_url=source_url,
        sketchfab_uid=uid,
        source_note=args.source_note,
    )


def run_sketchfab(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.token:
        return False, "no Sketchfab API token (--token or SKETCHFAB_API_TOKEN)"

    uid = extract_uid(args.sketchfab)
    slug = guess_slug(args.sketchfab, uid)
    ensure_dirs()
    work_dir = DATA_RAW / "_sketchfab_download"

    print(f"[fetch] metadata for {uid} ...")
    meta = fetch_metadata(uid)
    write_json(meta, DATA_RAW / "sketchfab_meta.json")

    print("[fetch] requesting download link ...")
    gltf_url = request_download_url(uid, args.token)

    print("[fetch] downloading and unpacking glTF archive ...")
    zip_path = work_dir / "archive.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    download_file(gltf_url, zip_path)
    src_dir = unzip_archive(zip_path, work_dir / "gltf_src")
    model_in = find_model_file(src_dir)

    dest = DATA_RAW / f"{slug}{model_in.suffix.lower()}"
    dest.write_bytes(model_in.read_bytes())

    info = source_info_from_sketchfab(meta, args.sketchfab, uid, args)
    info["model_file"] = dest.name
    write_json(info, DATA_RAW / "source_info.json")

    # Raw download intermediates are not the deliverable and would make the
    # step non-reproducible-looking in git status (they are re-derived from
    # the network every time fetch runs, not from data already in the repo).
    zip_path.unlink(missing_ok=True)
    for path in sorted(src_dir.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    src_dir.rmdir()
    work_dir.rmdir()

    todo_note = f", {len(info['todo_placeholders'])} TODO placeholder(s)" if info["todo_placeholders"] else ""
    message = f"fetched {dest.relative_to(DATA_RAW.parent)} from Sketchfab ({slug}){todo_note}"
    if info["todo_placeholders"]:
        message = "Warning: " + message + " -- title/creator/licence missing from Sketchfab metadata, pass --title/--creator/--licence"
    return True, message


# --------------------------------------------------------------------------
# Local-file path
# --------------------------------------------------------------------------

def run_local(args: argparse.Namespace) -> tuple[bool, str]:
    model_in = Path(args.local).expanduser().resolve()
    if not model_in.exists():
        return False, f"local file not found: {model_in}"

    warning = ""
    if model_in.suffix.lower() not in MODEL_SUFFIXES:
        warning = f"Warning: unexpected extension {model_in.suffix} -- Blender import will be attempted anyway. "

    ensure_dirs()
    slug = model_in.stem
    dest = DATA_RAW / f"{slug}{model_in.suffix.lower()}"
    dest.write_bytes(model_in.read_bytes())

    info = build_source_info(
        input_mode="local",
        slug=slug,
        model_file=dest.name,
        title=args.title,
        description=None,
        creator=args.creator,
        creator_profile=args.creator_profile,
        licence=args.licence,
        licence_url=args.licence_url,
        source_url=None,
        sketchfab_uid=None,
        source_note=args.source_note,
    )
    write_json(info, DATA_RAW / "source_info.json")

    todo_note = f", {len(info['todo_placeholders'])} TODO placeholder(s) in source_info.json" if info["todo_placeholders"] else ""
    message = f"{warning}fetched {dest.relative_to(DATA_RAW.parent)} from local file ({slug}){todo_note}"
    if info["todo_placeholders"] and not message.startswith("Warning"):
        message = "Warning: " + message + " -- pass --title/--creator/--licence, or fix them by hand before S5"
    return True, message


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def run(args: argparse.Namespace) -> tuple[bool, str]:
    sketchfab = getattr(args, "sketchfab", None)
    local = getattr(args, "local", None)
    if not sketchfab and not local:
        return False, "one of --sketchfab / --local is required for the fetch step"
    if sketchfab:
        return run_sketchfab(args)
    return run_local(args)


if __name__ == "__main__":
    import os

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sketchfab", metavar="URL")
    src.add_argument("--local", metavar="PATH")
    ap.add_argument("--token", default=os.environ.get("SKETCHFAB_API_TOKEN"))
    ap.add_argument("--title")
    ap.add_argument("--creator")
    ap.add_argument("--creator-profile")
    ap.add_argument("--licence")
    ap.add_argument("--licence-url")
    ap.add_argument("--source-note")
    ok, message = run(ap.parse_args())
    print(f"[fetch] {message}")
    raise SystemExit(0 if ok else 1)
