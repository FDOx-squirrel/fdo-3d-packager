"""fdo-3d-packager orchestrator -- the only entry point for this repository.

    python main.py                     all default (non-network) steps, in order
    python main.py --list              print steps and exit
    python main.py --only bundle       one step
    python main.py --from mdcff        this step and everything after
    python main.py --skip nexus        everything but this step
    python main.py --dry-run           print the plan, run nothing
    python main.py --strict            warnings become errors (this is what CI runs)
    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/..."
    python main.py --only fetch --local ./scans/rathealy_kiriengine.glb --title "..." --creator "..." --licence "..."

See PRIMER.md for what each step does and why. Steps are implemented one
module per step under py/, each independently runnable
(`python py/step_fetch.py ...`) -- this file is a convenience, not the only
path.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class Step:
    id: str
    module: str  # imported lazily as py.<module>
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    network: bool = False
    description: str = ""


# --------------------------------------------------------------------------
# STEPS table -- the source of truth for what this repo does and in what
# order. `network=True` steps are never part of the default run; call them
# by name (see PRIMER.md A3: "Netzwerkzugriff bleibt auf den fetch-Schritt
# beschraenkt").
# --------------------------------------------------------------------------

STEPS: list[Step] = [
    Step("fetch", "step_fetch", network=True,
         description="Resolve --sketchfab/--local into data/raw/."),
    Step("convert", "step_convert", depends_on=("fetch",),
         description="Blender: data/raw model -> dist/<slug>/model.obj + preview.png."),
    Step("nexus", "step_nexus", depends_on=("convert",),
         description="nxsbuild/nxscompress: dist/model.obj -> model.nxs/.nxz."),
    Step("mdcff", "step_mdcff", depends_on=("fetch", "nexus"),
         description="Write MD.cff + CITATION.cff, validate against MD.cff-schema.yaml."),
    Step("bundle", "step_bundle", depends_on=("convert", "nexus", "mdcff"),
         description="Assemble dist/<slug>.zip in fdo-squirrel's expected layout."),
    Step("build_fdo", "step_build_fdo", depends_on=("bundle",),
         description="Run dist/<slug>.zip through fdo-squirrel; fdo-metadata.ttl as proof."),
]

STEP_IDS = [s.id for s in STEPS]
STEP_BY_ID = {s.id: s for s in STEPS}


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="Print steps and exit.")
    ap.add_argument("--only", metavar="STEP", help="Run exactly one step.")
    ap.add_argument("--from", dest="frm", metavar="STEP", help="Run this step and everything after.")
    ap.add_argument("--skip", metavar="STEP", help="Run everything but this step.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan, run nothing.")
    ap.add_argument("--strict", action="store_true", help="Warnings become errors (this is what CI runs).")

    # Source selection for the fetch step (S2). Accepted here already so
    # --list/--dry-run document the eventual interface even when fetch isn't
    # the selected step.
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--sketchfab", metavar="URL", help="Sketchfab model URL or UID (fetch step).")
    src.add_argument("--local", metavar="PATH", help="Local .glb/.gltf/.obj file (fetch step).")
    ap.add_argument("--token", default=os.environ.get("SKETCHFAB_API_TOKEN"),
                     help="Sketchfab API token (fetch step, --sketchfab only; default: env SKETCHFAB_API_TOKEN).")
    ap.add_argument("--title", help="Metadata override/source for --local (fetch step).")
    ap.add_argument("--creator", help="Metadata override/source for --local (fetch step).")
    ap.add_argument("--creator-profile", help="Metadata override/source for --local (fetch step).")
    ap.add_argument("--licence", help="Metadata override/source for --local (fetch step).")
    ap.add_argument("--licence-url", help="Metadata override/source for --local (fetch step).")
    ap.add_argument("--source-note", help="Free-text provenance note, e.g. 'KiriEngine, 180 photos, 2026-03' (fetch step).")

    # Blender binary for the convert step (S3). Accepted here already for
    # the same reason as --sketchfab/--local above.
    ap.add_argument("--blender-bin", default=os.environ.get("BLENDER_BIN", "blender"),
                     help="Blender executable, headless-capable (convert step; default: env BLENDER_BIN or 'blender').")

    # nxsbuild/nxscompress binaries for the nexus step (S4). Same pattern
    # as --blender-bin above.
    ap.add_argument("--nxsbuild-bin", default=os.environ.get("NXSBUILD_BIN", "nxsbuild"),
                     help="nxsbuild executable (nexus step; default: env NXSBUILD_BIN or 'nxsbuild').")
    ap.add_argument("--nxscompress-bin", default=os.environ.get("NXSCOMPRESS_BIN", "nxscompress"),
                     help="nxscompress executable (nexus step; default: env NXSCOMPRESS_BIN or 'nxscompress').")
    ap.add_argument("--nxsbuild-original-textures", action="store_true",
                     help="nxsbuild -O: use original textures, skip atlas repacking. CAUTION: confirmed "
                          "against a real run to produce a texture-less .nxz (nxscompress reports "
                          "'Textures: 0') -- not recommended, kept as an opt-in escape hatch (nexus step).")
    ap.add_argument("--nxsbuild-ram", type=int, default=None, metavar="MB",
                     help="nxsbuild -r <MB>: RAM budget, nxsbuild's own default is 2000 (nexus step).")
    return ap


def _check_known(step_id: Optional[str]) -> None:
    if step_id and step_id not in STEP_BY_ID:
        raise SystemExit(f"Unknown step: {step_id} (known: {', '.join(STEP_IDS)})")


def resolve_selection(args: argparse.Namespace) -> list[str]:
    _check_known(args.only)
    _check_known(args.frm)
    _check_known(args.skip)

    if args.only:
        return [args.only]

    if not args.frm and not args.skip:
        # Default run: every non-network step, in order.
        return [s.id for s in STEPS if not s.network]

    ids = list(STEP_IDS)
    if args.frm:
        ids = ids[ids.index(args.frm):]
    if args.skip:
        ids = [i for i in ids if i != args.skip]
    return ids


def print_list() -> None:
    print(f"{'id':<10} {'depends_on':<24} {'network':<8} description")
    for s in STEPS:
        deps = ",".join(s.depends_on) or "-"
        print(f"{s.id:<10} {deps:<24} {str(s.network):<8} {s.description}")


def run_step(step: Step, args: argparse.Namespace) -> tuple[bool, str]:
    """Import the step module lazily and call its run(args). Every step
    module stays runnable standalone too (python py/step_<id>.py)."""
    mod = importlib.import_module(f"py.{step.module}")
    fn: Callable[[argparse.Namespace], tuple[bool, str]] = getattr(mod, "run")
    return fn(args)


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.list:
        print_list()
        return 0

    selection = resolve_selection(args)

    if args.dry_run:
        print("Plan (dry run, nothing executed):")
        for step_id in selection:
            print(f"  - {step_id}")
        return 0

    timings: list[tuple[str, float]] = []
    had_warning = False
    for step_id in selection:
        step = STEP_BY_ID[step_id]
        start = time.monotonic()
        try:
            ok, message = run_step(step, args)
        except Exception as exc:  # noqa: BLE001 -- report, do not swallow
            print(f"[{step_id}] ERROR: {exc}", file=sys.stderr)
            return 1
        elapsed = time.monotonic() - start
        timings.append((step_id, elapsed))
        print(f"[{step_id}] {message} ({elapsed:.2f}s)")
        if not ok:
            print(f"[{step_id}] step reported failure, stopping.", file=sys.stderr)
            return 1
        if message.lower().startswith("warning"):
            had_warning = True

    total = sum(t for _, t in timings) or 1e-9
    print("\nTiming:")
    for step_id, elapsed in timings:
        print(f"  {step_id:<10} {elapsed:6.2f}s  {100 * elapsed / total:5.1f}%")

    if args.strict and had_warning:
        print("\n--strict: warnings present, failing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
