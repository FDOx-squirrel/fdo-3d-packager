"""render_infrastructure_diagram.py -- docs/infrastructure.mmd -> docs/infrastructure.jpg.

Not a pipeline step (no entry in main.py's STEPS table) -- this renders a
documentation asset, not part of the fetch->build_fdo chain, run by hand
whenever docs/infrastructure.mmd changes, not on every `python main.py`.

Same rendering approach `fdo-squirrel` already uses for its own
fdo_overview.jpg (fdo_finalize.py:render_mermaid_to_jpg, copied here per
PRIMER.md A3 -- reuse means copying, not referencing): `mmdc` (Mermaid
CLI) doesn't support JPG output directly (only .svg/.png/.pdf/.md), so
this renders to a temporary high-resolution PNG first, then converts with
Pillow. Needs Node.js + `npm install -g @mermaid-js/mermaid-cli` and
`pip install Pillow` -- neither is in requirements.txt, both are
documentation-tooling-only, not needed to run the actual pipeline (same
reasoning fdo-squirrel's own README gives for keeping the Mermaid render
out of its base dependencies).

Headless Chromium refuses to launch as root without --no-sandbox (true in
this repo's own CI containers and in a Docker-based local setup) --
this script adds it unconditionally when running as root, same as
fdo-squirrel's own version; harmless everywhere else since it's simply not
added there.

Usage: python docs/render_infrastructure_diagram.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

DOCS_DIR = Path(__file__).resolve().parent
MMD_PATH = DOCS_DIR / "infrastructure.mmd"
JPG_PATH = DOCS_DIR / "infrastructure.jpg"


def render_mermaid_to_jpg(
    mermaid_path: Path,
    jpg_path: Path,
    width: int = 2400,
    height: int = 1600,
    scale: int = 2,
    timeout: int = 120,
) -> Optional[Path]:
    """Render `mermaid_path` to a high-resolution JPG at `jpg_path`.

    Returns the output path on success, None on failure (a message is
    printed either way -- never raises, so a missing `mmdc`/Pillow doesn't
    break anything that isn't this one documentation asset).
    """
    if not mermaid_path.exists():
        print(f"✘ {mermaid_path} not found")
        return None

    mmdc = shutil.which("mmdc") or shutil.which("mmdc.cmd")
    if not mmdc:
        print(
            "⚠ Render skipped: 'mmdc' not found on PATH.\n"
            "   Install Node.js, then run:\n"
            "     npm install -g @mermaid-js/mermaid-cli\n"
            "   to enable the high-resolution JPG render."
        )
        return None

    try:
        from PIL import Image
    except ImportError:
        print(
            "⚠ Render skipped: Pillow is not installed.\n"
            "   Run `pip install Pillow` to enable the PNG->JPG conversion."
        )
        return None

    tmp_png = jpg_path.with_suffix(".tmp.png")
    tmp_cfg: Optional[Path] = None
    cmd = [
        mmdc, "-i", str(mermaid_path), "-o", str(tmp_png),
        "-w", str(width), "-H", str(height),
        "--backgroundColor", "white", "--scale", str(scale),
    ]

    # Same guard as fdo-squirrel's own render_mermaid_to_jpg (A3): headless
    # Chromium refuses to launch as root without --no-sandbox.
    try:
        is_root = hasattr(os, "geteuid") and os.geteuid() == 0
    except Exception:
        is_root = False
    if is_root:
        tmp_cfg = jpg_path.with_suffix(".puppeteer.json")
        tmp_cfg.write_text(json.dumps({"args": ["--no-sandbox"]}), encoding="utf-8")
        cmd += ["--puppeteerConfigFile", str(tmp_cfg)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
        with Image.open(tmp_png) as im:
            im.convert("RGB").save(jpg_path, "JPEG", quality=92, optimize=True)
        print(f"✔ Rendered {jpg_path.relative_to(DOCS_DIR.parent)}")
        return jpg_path
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace").strip()
        print(f"⚠ Render skipped: mmdc failed - {stderr[-500:]}")
        return None
    except Exception as e:
        print(f"⚠ Render skipped: {e}")
        return None
    finally:
        if tmp_png.exists():
            tmp_png.unlink()
        if tmp_cfg is not None and tmp_cfg.exists():
            tmp_cfg.unlink()


def main() -> int:
    result = render_mermaid_to_jpg(MMD_PATH, JPG_PATH)
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
