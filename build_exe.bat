@echo off
title Pulse Remote - Build Standalone EXE
cd /d "%~dp0"

echo ======================================================
echo    ⚡ Building Standalone Windows Executable (.exe)
echo ======================================================
echo.

python build_exe.py
pause
