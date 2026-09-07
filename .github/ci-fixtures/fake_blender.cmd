@echo off
REM Windows wrapper for fake_blender.py -- PRIMER.md S9.
REM
REM subprocess.run([blender_bin, ...], check=True) (step_convert.py) execs
REM blender_bin directly, no shell=True -- a bare .py file can't be
REM launched that way on Windows without shell=True (there is no exec-bit
REM concept, and CreateProcess does not consult file associations the way
REM double-clicking in Explorer does). A .cmd *can* -- Windows' process
REM launcher special-cases .bat/.cmd and runs them through cmd.exe even
REM without shell=True. So this thin wrapper is what --blender-bin should
REM point at on Windows; fake_blender.py itself stays the one used by CI
REM (Linux runner, chmod +x, no wrapper needed there).
REM
REM %~dp0 is this .cmd's own directory (trailing backslash included), so
REM this finds fake_blender.py next to it regardless of the caller's
REM working directory. %* forwards every argument unchanged.
python "%~dp0fake_blender.py" %*
