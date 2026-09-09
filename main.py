"""fdo-3d-packager orchestrator -- the only entry point for this repository.

    python main.py                     all default (non-network) steps, in order
    python main.py --list              print steps and exit
    python main.py --only bundle       one step
    python main.py --from mdcff        this step and everything after
    python main.py --skip nexus        everything but this step
    python main.py --dry-run           print the plan, run nothing
    python main.py --strict            warnings become errors (this is what CI runs)
    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/..."
    python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/aaa..." --sketchfab "https://sketchfab.com/3d-models/bbb..."
    python main.py --only fetch --local ./scans/rathealy_kiriengine.glb --title "..." --creator "..." --licence "..."
    python main.py --only mdcff --publisher-label "Research Squirrel Engineers Network" --publisher-id "https://github.com/Research-Squirrel-Engineers"
    python main.py --slug govan-2                        run the default pipeline for one fetched model
    python main.py --all-slugs                            run the default pipeline for every fetched model
    python main.py --from fetch --sketchfab "..." --sketchfab "..." --nxsbuild-bin ... --publisher-label ...
        fetch, then automatically run the rest of the selection (convert
        onwards) for exactly the model(s) just fetched -- --slug/--all-slugs
        are not needed (and are ignored with a note if passed) since fetch
        already tells the rest of the run which slug(s) to use.
    python main.py --from fetch --sketchfab "..." --publisher-label ... --publish-only
        same, but once build_fdo confirms the round trip, delete every
        intermediate for that slug except dist/<slug>_release/
        <slug>-fdo-bundle.zip -- the one self-contained deliverable.

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

from py.fdo_3d_packager_utils import (
    discover_bundle_slugs,
    discover_slugs,
    publish_only_cleanup,
    resolve_bundle_slug,
)


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
    ap.add_argument("--publish-only", action="store_true",
                     help="After a run that includes build_fdo succeeds, delete dist/<slug>/, "
                          "dist/<slug>.zip and everything in dist/<slug>_release/ except "
                          "<slug>-fdo-bundle.zip (S11) -- that bundle is already self-contained, "
                          "nothing is lost. Opt-in; the default keeps every intermediate, which "
                          "--from/--skip reruns depend on. No-op (with a note) if build_fdo isn't "
                          "part of this run.")

    # Which fetched model(s) to run the selected step(s) against
    # (convert/nexus/mdcff, S3-S5; bundle/build_fdo once they exist).
    # Nachtrag 2026-09-07 (3): data/raw/source_info.json moved from a
    # single top-level file to one per slug (data/raw/<slug>/), so a step
    # needs to be told which one when more than one has been fetched --
    # --slug picks one, --all-slugs loops every step in `selection` over
    # every slug found. With exactly one slug fetched, neither flag is
    # needed (auto-detected, see fdo_3d_packager_utils.py:resolve_slug()).
    # Nachtrag 2026-09-07 (6): both are ignored (with a printed note, not
    # an error) when `fetch` is part of the same run -- see main()'s own
    # handling of that case.
    ap.add_argument("--slug", help="Which fetched model (data/raw/<slug>/) to act on. Auto-detected if exactly one exists; ignored if fetch runs in the same invocation.")
    ap.add_argument("--all-slugs", action="store_true",
                     help="Run the selected step(s) for every fetched model under data/raw/, one after another. Not combinable with --slug; ignored (with a note) if fetch runs in the same invocation.")

    # Source selection for the fetch step (S2). Accepted here already so
    # --list/--dry-run document the eventual interface even when fetch isn't
    # the selected step. --sketchfab is repeatable for a batch fetch
    # (Nachtrag 2026-09-07 (3)) -- --sketchfab URL1 --sketchfab URL2 ...
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--sketchfab", action="append", metavar="URL",
                      help="Sketchfab model URL or UID (fetch step). Repeatable for a batch fetch.")
    src.add_argument("--local", metavar="PATH", help="Local .glb/.gltf/.obj file (fetch step).")
    ap.add_argument("--token", default=os.environ.get("SKETCHFAB_API_TOKEN"),
                     help="Sketchfab API token (fetch step, --sketchfab only; default: env SKETCHFAB_API_TOKEN).")
    ap.add_argument("--title", help="Metadata override/source for --local (fetch step). Not usable with more than one --sketchfab URL.")
    ap.add_argument("--creator", help="Metadata override/source for --local (fetch step). Not usable with more than one --sketchfab URL.")
    ap.add_argument("--creator-profile", help="Metadata override/source for --local (fetch step). Not usable with more than one --sketchfab URL.")
    ap.add_argument("--licence", help="Metadata override/source for --local (fetch step). Not usable with more than one --sketchfab URL.")
    ap.add_argument("--licence-url", help="Metadata override/source for --local (fetch step). Not usable with more than one --sketchfab URL.")
    ap.add_argument("--source-note", help="Free-text provenance note, e.g. 'KiriEngine, 180 photos, 2026-03' (fetch step). Not usable with more than one --sketchfab URL.")

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

    # Publisher for MD.cff (mdcff step, S5). No hardcoded default
    # (PRIMER.md A4) -- falls back to FDO_PUBLISHER_LABEL/FDO_PUBLISHER_ID
    # env vars (same pattern as --blender-bin/BLENDER_BIN), still required
    # one way or the other.
    ap.add_argument("--publisher-label", default=os.environ.get("FDO_PUBLISHER_LABEL"),
                     help="MD.cff publishers[0].label. Required for mdcff (or set FDO_PUBLISHER_LABEL env var), no hardcoded default (mdcff step).")
    ap.add_argument("--publisher-id", default=os.environ.get("FDO_PUBLISHER_ID"),
                     help="MD.cff publishers[0].id, e.g. a GitHub/ROR URL (or set FDO_PUBLISHER_ID env var). Optional (mdcff step).")
    return ap


def _check_known(step_id: Optional[str]) -> None:
    if step_id and step_id not in STEP_BY_ID:
        raise SystemExit(f"Unknown step: {step_id} (known: {', '.join(STEP_IDS)})")


def resolve_selection(args: argparse.Namespace) -> list[str]:
    """Just the step-id resolution (--only/--from/--skip/default) --
    slug-selection validation (--slug vs --all-slugs vs fetch being part of
    the run) lives in main() now, since whether fetch is present changes
    what --slug/--all-slugs even mean (Nachtrag 2026-09-07 (6))."""
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


def _discover_slugs_for(selection: list[str]) -> list[str]:
    """Which slugs `--all-slugs` should loop `selection` over.

    Found the hard way (S9): every step but `build_fdo` resolves its own
    slug via data/raw/<slug>/source_info.json (resolve_slug(), see
    fdo_3d_packager_utils.py), so `discover_slugs()` (data/raw/-based) is
    the right source for any selection touching one of those -- but
    `build_fdo` (S7) resolves against dist/<slug>.zip instead
    (resolve_bundle_slug(), deliberately data/raw/-independent, see its own
    docstring), so a `--only build_fdo --all-slugs` run has no business
    requiring data/raw/ to exist at all. `selection` only ever equals
    `["build_fdo"]` via `--only build_fdo` or `--from build_fdo` (it's last
    in STEPS, and `--skip` takes a single step, so no other combination
    isolates it) -- every other selection includes at least one
    data/raw/-based step, for which `discover_slugs()` remains correct."""
    if selection == ["build_fdo"]:
        return discover_bundle_slugs()
    return discover_slugs()


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


def run_selection_once(selection: list[str], args: argparse.Namespace) -> tuple[Optional[int], bool]:
    """Runs `selection` once against whatever `args.slug` currently points
    at (None is fine -- resolve_slug() inside load_source_info() picks the
    single fetched model, or the per-step code raises a clear error).
    Returns (exit_code_or_None, had_warning) -- exit_code is None only when
    every step in the selection succeeded, so main() can tell "this slug
    failed" apart from "this slug is done, warnings noted"."""
    timings: list[tuple[str, float]] = []
    had_warning = False
    for step_id in selection:
        step = STEP_BY_ID[step_id]
        start = time.monotonic()
        try:
            ok, message = run_step(step, args)
        except Exception as exc:  # noqa: BLE001 -- report, do not swallow
            print(f"[{step_id}] ERROR: {exc}", file=sys.stderr)
            return 1, had_warning
        elapsed = time.monotonic() - start
        timings.append((step_id, elapsed))
        print(f"[{step_id}] {message} ({elapsed:.2f}s)")
        if not ok:
            print(f"[{step_id}] step reported failure, stopping.", file=sys.stderr)
            return 1, had_warning
        if message.lower().startswith("warning"):
            had_warning = True

    total = sum(t for _, t in timings) or 1e-9
    print("\nTiming:")
    for step_id, elapsed in timings:
        print(f"  {step_id:<10} {elapsed:6.2f}s  {100 * elapsed / total:5.1f}%")

    if getattr(args, "publish_only", False):
        if "build_fdo" in selection:
            # Resolved *before* publish_only_cleanup runs -- it deletes
            # dist/<slug>.zip, which is what this resolution reads.
            slug = resolve_bundle_slug(getattr(args, "slug", None))
            removed = publish_only_cleanup(slug)
            if removed:
                print(
                    f"[publish-only] {slug}: removed {len(removed)} intermediate path(s), "
                    f"kept dist/{slug}_release/{slug}-fdo-bundle.zip"
                )
                for path in removed:
                    print(f"  - {path}")
            else:
                print(f"[publish-only] {slug}: nothing to remove (already clean)")
        else:
            print(
                "[publish-only] ignored: build_fdo not part of this run, nothing to publish yet",
                file=sys.stderr,
            )

    return None, had_warning


def run_over_slugs(selection: list[str], slugs: list[str], args: argparse.Namespace) -> tuple[int, bool]:
    """Runs `selection` once per slug in `slugs`.

    Nachtrag 2026-09-07 (6): a failing slug no longer aborts the whole run
    when more than one slug is in play -- each is independent (same
    reasoning as the batch-fetch loop in step_fetch.py: one bad model
    shouldn't cost you the other nine), and the run only fails outright if
    *every* slug failed. With a single slug (the pre-batch, still by far
    the most common case), a failure still returns immediately -- there is
    nothing to "continue past". Returns (exit_code, had_warning)."""
    had_warning = False
    failed: list[str] = []
    for slug in slugs:
        if len(slugs) > 1:
            print(f"\n=== slug: {slug} ===")
        args.slug = slug
        exit_code, slug_had_warning = run_selection_once(selection, args)
        if exit_code is not None:
            if len(slugs) == 1:
                return exit_code, had_warning
            failed.append(slug)
            continue
        had_warning = had_warning or slug_had_warning

    if failed:
        if len(failed) == len(slugs):
            print(f"\nAll {len(slugs)} slug(s) failed: {', '.join(failed)}", file=sys.stderr)
            return 1, had_warning
        print(f"\nWarning: {len(failed)}/{len(slugs)} slug(s) failed: {', '.join(failed)}", file=sys.stderr)
        had_warning = True
    return 0, had_warning


def _run_fetch_then_rest(selection: list[str], args: argparse.Namespace) -> int:
    """`fetch` is part of `selection` -- Nachtrag 2026-09-07 (6): run it
    exactly once (never per-slug; slugs don't exist yet), then continue
    the rest of `selection` for exactly the model(s) it just fetched --
    read off args.fetched_slugs, which step_fetch.py's run() sets on
    success (see its own docstring). --slug/--all-slugs are ignored here
    (noted, not an error) since fetch already answers the "which slug(s)"
    question more precisely than either could: --all-slugs would also
    reprocess unrelated older fetches, and --slug can't name a model that
    doesn't exist until fetch has run."""
    if args.slug or args.all_slugs:
        print(
            "[fetch] --slug/--all-slugs ignored: fetch is part of this run, "
            "continuing with the model(s) just fetched instead",
            file=sys.stderr,
        )

    start = time.monotonic()
    try:
        ok, message = run_step(STEP_BY_ID["fetch"], args)
    except Exception as exc:  # noqa: BLE001 -- report, do not swallow
        print(f"[fetch] ERROR: {exc}", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - start
    print(f"[fetch] {message} ({elapsed:.2f}s)")
    if not ok:
        print("[fetch] step reported failure, stopping.", file=sys.stderr)
        return 1
    fetch_had_warning = message.lower().startswith("warning")

    rest = [s for s in selection if s != "fetch"]
    if not rest:
        # --only fetch: nothing left to chain, just report fetch's own result.
        if args.strict and fetch_had_warning:
            print("\n--strict: warnings present, failing.", file=sys.stderr)
            return 1
        return 0

    slugs = getattr(args, "fetched_slugs", None) or []
    if not slugs:
        # ok=True should always come with at least one slug (module
        # contract of step_fetch.py:run()) -- guard anyway rather than
        # silently iterating zero times if that contract is ever violated.
        print("[fetch] reported success but named no fetched slug(s) to continue with", file=sys.stderr)
        return 1

    exit_code, had_warning = run_over_slugs(rest, slugs, args)
    if exit_code != 0:
        return exit_code
    if args.strict and (fetch_had_warning or had_warning):
        print("\n--strict: warnings present, failing.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    args = build_arg_parser().parse_args()
    args.fetched_slugs = None  # set by step_fetch.py's run() on success

    if args.list:
        print_list()
        return 0

    selection = resolve_selection(args)

    if args.dry_run:
        print("Plan (dry run, nothing executed):")
        for step_id in selection:
            print(f"  - {step_id}")
        if "fetch" in selection:
            print("\nfetch is part of this run: the rest would continue with "
                  "whichever model(s) it fetches, not --all-slugs discovery.")
        elif args.all_slugs:
            slugs = _discover_slugs_for(selection)
            print(f"\n--all-slugs: would run the above for {len(slugs)} slug(s): {', '.join(slugs) or '(none found)'}")
        return 0

    if "fetch" in selection:
        return _run_fetch_then_rest(selection, args)

    if args.all_slugs and args.slug:
        print("--all-slugs and --slug are mutually exclusive -- pick one", file=sys.stderr)
        return 1

    if args.all_slugs:
        slugs = _discover_slugs_for(selection)
        if not slugs:
            if selection == ["build_fdo"]:
                print("--all-slugs: no dist/<slug>.zip found -- run bundle first", file=sys.stderr)
            else:
                print("--all-slugs: no data/raw/<slug>/source_info.json found -- run fetch first", file=sys.stderr)
            return 1
    else:
        slugs = [args.slug]  # a single None is fine -- resolve_slug() auto-detects

    exit_code, had_warning = run_over_slugs(selection, slugs, args)
    if exit_code != 0:
        return exit_code
    if args.strict and had_warning:
        print("\n--strict: warnings present, failing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
