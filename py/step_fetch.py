"""fetch -- resolve --sketchfab/--local into data/raw/.

The only step allowed to touch the network (Sketchfab Data/Download API).
Not part of the default `python main.py` run; call it explicitly:

    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/..."
    python main.py --only fetch --local ./scans/rathealy_kiriengine.glb --title "..." --creator "..." --licence "..."

S2: migrated from the sketchfab_fdo_prototype in the neighbouring chat --
Sketchfab Data API metadata harvest + Download API request for --sketchfab,
or a local-file copy/validate for --local. Writes the model file plus every
sibling file it references (see resolve_sibling_files()) to
data/raw/<slug>/, and data/raw/source_info.json (the S2/S3/S4/S5 handoff
contract -- see build_source_info() docstring) recording `model_file` as
the path *relative to data/raw/*. For --sketchfab, the raw API response
also goes to data/raw/sketchfab_meta.json for audit (matches the
prototype's convention).

Befund 2026-09-04 (first real --sketchfab run, "Donaghmore Church ruin"):
the original version of this step copied only the .gltf file itself and
silently dropped scene.bin (the actual mesh, referenced via
buffers[].uri) and every textures/*.jpeg image (images[].uri) -- both of
which every real Sketchfab glTF export splits out as separate files.
Blender (S3) would have failed on every real model with a "file not
found" error inside the .gltf's own relative-URI resolution. Fixed here by
resolving and copying those siblings alongside the model file, preserving
their relative sub-paths (e.g. textures/foo.jpeg) so the relative URIs
inside the model keep resolving from its new location. .glb has no such
siblings (self-contained binary); --local .obj can have the same problem
via its mtllib/map_* references, fixed the same way.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

import requests

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone
# (`python py/step_*.py` -- repo root is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import DATA_RAW, MTL_TEXTURE_KEYS, ensure_dirs, write_json

SKETCHFAB_API = "https://api.sketchfab.com/v3"
UID_RE = re.compile(r"([0-9a-f]{32})")
MODEL_SUFFIXES = (".glb", ".gltf", ".obj")


# --------------------------------------------------------------------------
# Sibling-file resolution (Befund 2026-09-04, see module docstring)
# --------------------------------------------------------------------------

def _gltf_sibling_uris(gltf_path: Path) -> tuple[list[str], list[str]]:
    """buffers[].uri / images[].uri that are external files (not embedded
    data: URIs), as relative paths from gltf_path's own directory -- the
    only place a .gltf's relative URIs are resolved against. .glb embeds
    everything and is not routed here."""
    doc = json.loads(gltf_path.read_text(encoding="utf-8"))
    uris = [
        unquote(entry["uri"])
        for section in ("buffers", "images")
        for entry in doc.get(section, [])
        if entry.get("uri") and not entry["uri"].startswith("data:")
    ]
    existing = [u for u in uris if (gltf_path.parent / u).exists()]
    missing = [u for u in uris if u not in existing]
    return existing, missing


def _obj_sibling_uris(obj_path: Path) -> tuple[list[str], list[str]]:
    """The mtllib target plus every texture it references (MTL_TEXTURE_KEYS),
    resolved relative to the .obj's own directory -- the usual
    KiriEngine/Blender export convention of .mtl + textures sitting next to
    the .obj."""
    mtl_name = None
    for line in obj_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().lower().startswith("mtllib "):
            mtl_name = line.strip().split(None, 1)[1].strip()
            break
    if not mtl_name:
        return [], []

    mtl_path = obj_path.parent / mtl_name
    if not mtl_path.exists():
        return [], [mtl_name]

    existing, missing = [mtl_name], []
    for line in mtl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0] in MTL_TEXTURE_KEYS:
            tex_name = parts[1].split()[-1]  # options like -o/-s may precede it
            (existing if (obj_path.parent / tex_name).exists() else missing).append(tex_name)
    return existing, missing


def resolve_sibling_files(model_path: Path) -> tuple[list[str], list[str]]:
    """Sibling files model_path references via relative URI/path that must
    travel with it for Blender (S3) to import it successfully. Returns
    (existing relative paths, missing ones); .glb has none by convention
    (self-contained)."""
    suffix = model_path.suffix.lower()
    if suffix == ".gltf":
        return _gltf_sibling_uris(model_path)
    if suffix == ".obj":
        return _obj_sibling_uris(model_path)
    return [], []


def copy_model_with_siblings(model_in: Path, slug: str) -> tuple[Path, list[str], list[str]]:
    """Copy model_in plus its resolved siblings into a clean data/raw/<slug>/,
    preserving their relative sub-paths. Returns (dest model path, sibling
    paths copied, sibling paths referenced but missing on disk -- the
    latter is non-fatal here but will make S3 fail for real)."""
    slug_dir = DATA_RAW / slug
    if slug_dir.exists():
        shutil.rmtree(slug_dir)  # no stale siblings from a previous fetch
    slug_dir.mkdir(parents=True)

    dest = slug_dir / f"{slug}{model_in.suffix.lower()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(model_in, dest)

    existing, missing = resolve_sibling_files(model_in)
    for rel in existing:
        target = slug_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(model_in.parent / rel, target)

    return dest, existing, missing


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
    """Befund 2026-09-07: `user.profileUrl` is already in the Data API v3
    response (confirmed against real-world usage, not just the API's own
    docs) -- use it directly instead of only reconstructing
    `https://sketchfab.com/{username}` by hand; the constructed form stays
    as a fallback for the (currently unobserved) case that profileUrl is
    missing."""
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
        creator_profile=args.creator_profile or user.get("profileUrl")
        or (f"https://sketchfab.com/{username}" if username else None),
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

    dest, siblings, missing_siblings = copy_model_with_siblings(model_in, slug)

    info = source_info_from_sketchfab(meta, args.sketchfab, uid, args)
    info["model_file"] = str(dest.relative_to(DATA_RAW))
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
    sibling_note = f", +{len(siblings)} sibling file(s)" if siblings else ""
    message = f"fetched {dest.relative_to(DATA_RAW.parent)} from Sketchfab ({slug}){sibling_note}{todo_note}"
    warn_reasons = []
    if info["todo_placeholders"]:
        warn_reasons.append("title/creator/licence missing from Sketchfab metadata, pass --title/--creator/--licence")
    if missing_siblings:
        warn_reasons.append(f"referenced sibling file(s) missing, S3 will fail to import: {', '.join(missing_siblings)}")
    if warn_reasons:
        message = "Warning: " + message + " -- " + "; ".join(warn_reasons)
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
    dest, siblings, missing_siblings = copy_model_with_siblings(model_in, slug)

    info = build_source_info(
        input_mode="local",
        slug=slug,
        model_file=str(dest.relative_to(DATA_RAW)),
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
    sibling_note = f", +{len(siblings)} sibling file(s)" if siblings else ""
    message = f"{warning}fetched {dest.relative_to(DATA_RAW.parent)} from local file ({slug}){sibling_note}{todo_note}"
    warn_reasons = []
    if info["todo_placeholders"]:
        warn_reasons.append("pass --title/--creator/--licence, or fix them by hand before S5")
    if missing_siblings:
        warn_reasons.append(f"referenced sibling file(s) missing, S3 will fail to import: {', '.join(missing_siblings)}")
    if warn_reasons and not message.startswith("Warning"):
        message = "Warning: " + message + " -- " + "; ".join(warn_reasons)
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
