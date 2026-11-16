"""run_log -- keep the whole terminal output of a run in a file (PRIMER.md S19).

`python main.py ... --log dist/<slug>-run-log.md` copies everything the run
prints -- the step messages, Blender, nxsbuild, fdo-squirrel and the
RO-Crate validator -- to the console *and* to that file. A `.md` path gets a
small header and the output in a fenced block, any other path (`.txt`) the
same header as plain lines. The header records date, command line (a
`--token` value is replaced by `***`), working directory, Python and
platform; the footer records the exit code.

Child processes only show up in the file because they run through
`py.fdo_3d_packager_utils.run_command()`, which switches to line-by-line
capture while a log is active (see there). Without `--log` nothing here is
imported and the console behaviour is unchanged.
"""
from __future__ import annotations

import datetime
import platform
import sys
import traceback
from pathlib import Path

from py.fdo_3d_packager_utils import set_capture_child_output

FENCE = "````"


def redact_argv(argv: list[str]) -> list[str]:
    """argv with the value of any option whose name contains 'token' hidden."""
    out: list[str] = []
    hide_next = False
    for arg in argv:
        if hide_next:
            out.append("***")
            hide_next = False
        elif arg.startswith("--") and "token" in arg.lower():
            if "=" in arg:
                out.append(arg.split("=", 1)[0] + "=***")
            else:
                out.append(arg)
                hide_next = True
        else:
            out.append(arg)
    return out


class _Tee:
    """Writes to the real stream and to the log file; everything else
    (isatty, encoding, fileno, ...) is the real stream's."""

    def __init__(self, stream, sink) -> None:
        self._stream = stream
        self._sink = sink

    def write(self, text: str) -> int:
        written = self._stream.write(text)
        self._sink.write(text)
        return len(text) if written is None else written

    def flush(self) -> None:
        self._stream.flush()
        self._sink.flush()

    def __getattr__(self, name: str):
        return getattr(self._stream, name)


class RunLog:
    """Context manager: `with RunLog(path, argv): ...`. Re-raises whatever
    the body raises, after writing the traceback and the footer."""

    def __init__(self, path: str, argv: list[str]) -> None:
        self.path = Path(path)
        self.argv = argv
        self.markdown = self.path.suffix.lower() == ".md"
        self._sink = None
        self._saved: tuple | None = None
        self.exit_code: int | None = None

    def __enter__(self) -> "RunLog":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sink = open(self.path, "w", encoding="utf-8", errors="replace", newline="\n")
        command = "python " + " ".join(_quote(a) for a in redact_argv(self.argv))
        started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        if self.markdown:
            self._sink.write(
                "# fdo-3d-packager run log\n\n"
                f"- Started: {started}\n"
                f"- Command: `{command}`\n"
                f"- Working directory: `{Path.cwd()}`\n"
                f"- Python {platform.python_version()} on {platform.platform()}\n\n"
                f"{FENCE}text\n"
            )
        else:
            self._sink.write(
                "fdo-3d-packager run log\n"
                f"Started: {started}\n"
                f"Command: {command}\n"
                f"Working directory: {Path.cwd()}\n"
                f"Python {platform.python_version()} on {platform.platform()}\n"
                + "-" * 78 + "\n"
            )
        self._saved = (sys.stdout, sys.stderr)
        sys.stdout = _Tee(sys.stdout, self._sink)
        sys.stderr = _Tee(sys.stderr, self._sink)
        set_capture_child_output(True)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        set_capture_child_output(False)
        if self._saved:
            sys.stdout.flush()
            sys.stderr.flush()
            sys.stdout, sys.stderr = self._saved
        assert self._sink is not None
        if exc_type is not None:
            self._sink.write("".join(traceback.format_exception(exc_type, exc, tb)))
        status = "exception" if exc_type is not None else (
            "unknown" if self.exit_code is None else str(self.exit_code)
        )
        if self.markdown:
            self._sink.write(f"\n{FENCE}\n\nExit code: {status}\n")
        else:
            self._sink.write("-" * 78 + f"\nExit code: {status}\n")
        self._sink.close()
        print(f"[log] run log written to {self.path}")
        return False


def _quote(arg: str) -> str:
    return f'"{arg}"' if (not arg or any(c in arg for c in " \t&|<>^")) else arg
