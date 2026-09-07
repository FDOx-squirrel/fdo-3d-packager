@echo off
REM Windows wrapper for fake_nxsbuild.py -- see fake_blender.cmd in this
REM directory for the full reasoning, identical here.
python "%~dp0fake_nxsbuild.py" %*
