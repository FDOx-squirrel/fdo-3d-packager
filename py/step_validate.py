"""validate -- check the finished bundle's RO-Crate with rocrate-validator.

`build_fdo` (S7) leaves dist/<slug>_release/<slug>-fdo-bundle.zip, which
carries ro-crate-metadata.json at its root (RO-Crate 1.2 plus Signposting).
This step unpacks that ZIP into a scratch folder in the system temp
directory, runs `rocrate-validator validate <folder>` on it and removes the
folder again if the validator accepts the crate. The validator's own report
is printed as it is (and ends up in the run log, see `--log`).

It is the only step besides `fetch` that needs the network (`network=True`
in main.py's STEPS table): the validator downloads the JSON-LD context and
tries to resolve every profile IRI the crate declares. Offline it stops with
a URLError (exit code 2), which is a failed run, not a verdict on the crate.
The warning that the FDOx profile
`https://w3id.org/fdo-squirrel/profile/ro-crate/1.0` "could not be verified"
is expected, that profile is not registered with the validator.

`rocrate-validator` is not a requirement of this repo (`pip install
roc-validator`, tested with 0.13.1). If the executable cannot be found the
step is a Warning, not a failure (`--strict` makes it one), so a run that
predates this step does not fail at its very end.

Reads the bundle, not dist/_build/: `--publish-only` (S11) deletes the
latter and keeps the former.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Make `import py.fdo_3d_packager_utils` resolve whether this module is
# imported by main.py (repo root already on sys.path) or run standalone.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py.fdo_3d_packager_utils import release_dir, resolve_release_slug, run_command

# Only applied while a run log is written (see run_command()): a fixed width
# keeps the validator's boxed report readable in the file, UTF-8 keeps its
# box-drawing characters from failing on a Windows code page.
CAPTURE_ENV = {"COLUMNS": "140", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def _find_validator(explicit: str | None) -> str | None:
    if explicit:
        return explicit if (Path(explicit).exists() or shutil.which(explicit)) else None
    return shutil.which("rocrate-validator")


def run(args: argparse.Namespace) -> tuple[bool, str]:
    try:
        slug = resolve_release_slug(getattr(args, "slug", None))
    except (FileNotFoundError, ValueError) as exc:
        return False, str(exc)

    bundle = release_dir(slug) / f"{slug}-fdo-bundle.zip"
    if not bundle.exists():
        return False, f"{bundle} not found -- run `python main.py --only build_fdo` first"

    validator = _find_validator(getattr(args, "rocrate_validator_bin", None))
    if not validator:
        return True, (
            "Warning: rocrate-validator not found, RO-Crate not validated "
            "(pip install roc-validator, or pass --rocrate-validator-bin)"
        )

    crate_dir = Path(tempfile.mkdtemp(prefix=f"rocrate-{slug}-"))
    with zipfile.ZipFile(bundle) as zf:
        zf.extractall(crate_dir)
    if not (crate_dir / "ro-crate-metadata.json").exists():
        shutil.rmtree(crate_dir, ignore_errors=True)
        return False, f"{bundle.name} has no ro-crate-metadata.json at its root"

    try:
        run_command([validator, "validate", str(crate_dir)], capture_env=CAPTURE_ENV)
    except subprocess.CalledProcessError as exc:
        return False, (
            f"rocrate-validator exited with {exc.returncode} for {bundle.name} -- see its report above "
            f"(a URLError means it had no internet, not that the crate is wrong); crate kept in {crate_dir}"
        )
    shutil.rmtree(crate_dir, ignore_errors=True)
    return True, f"RO-Crate of {bundle.name} accepted by rocrate-validator"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rocrate-validator-bin", default=os.environ.get("ROCRATE_VALIDATOR_BIN"),
                     help="rocrate-validator executable (default: env ROCRATE_VALIDATOR_BIN, then $PATH).")
    ap.add_argument("--slug", help="Which finished bundle (dist/<slug>_release/) to validate. Auto-detected if exactly one exists.")
    ok, message = run(ap.parse_args())
    print(f"[validate] {message}")
    raise SystemExit(0 if ok else 1)
