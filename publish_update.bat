@echo off
setlocal enabledelayedexpansion
title Pulse Remote - 1-Click Update and Publish Tool
cd /d "%~dp0"
chcp 65001 > nul

cls
echo ====================================================================
echo             PULSE REMOTE 1-CLICK UPDATE ^& PUBLISH
echo ====================================================================
echo.
echo This tool will automatically:
echo   1. Build a fresh standalone PulseRemote.exe
echo   2. Copy the new .exe to your Desktop
echo   3. Commit and push the latest source code to GitHub
echo   4. Create a new GitHub Release and upload the .exe
echo   5. Automatically update the live website download link
echo.
echo ====================================================================
echo.

:ask_version
set "VERSION="
set /p VERSION="[?] Enter New Version Tag (e.g. v2.1.0): "
if "%VERSION%"=="" (
    echo [!] Version tag cannot be empty. Please enter something like v2.1.0.
    goto ask_version
)

:ask_notes
set "NOTES="
set /p NOTES="[?] What's new in this update? (e.g. Bug fixes and speed improvements): "
if "%NOTES%"=="" (
    set NOTES=Updates and improvements for %VERSION%
)

echo.
echo --------------------------------------------------------------------
echo Target Version: %VERSION%
echo Release Notes:  %NOTES%
echo --------------------------------------------------------------------
echo.
set "CONFIRM=Y"
set /p CONFIRM="Proceed with Build and Publish? (Y/N, default Y): "
if /i "%CONFIRM%"=="N" (
    echo.
    echo Operation cancelled by user.
    pause
    exit /b 0
)

echo.
echo ====================================================================
echo [Step 1/4] Compiling Standalone Executable (PyInstaller)...
echo ====================================================================
python build_exe.py
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Please check the error output above.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo [Step 2/4] Updating Desktop Copy...
echo ====================================================================
if exist "dist\PulseRemote.exe" (
    copy /y "dist\PulseRemote.exe" "%USERPROFILE%\Desktop\PulseRemote.exe" > nul
    echo [OK] Fresh PulseRemote.exe copied to Desktop.
) else (
    echo [WARNING] dist\PulseRemote.exe not found!
)

echo.
echo ====================================================================
echo [Step 3/4] Committing ^& Pushing Code to GitHub...
echo ====================================================================
git add .
git commit -m "Release %VERSION%: %NOTES%"
git push origin master
if errorlevel 1 (
    echo.
    echo [WARNING] Git push encountered an issue, but continuing to release...
) else (
    echo [OK] Source code pushed to master branch successfully.
)

echo.
echo ====================================================================
echo [Step 4/4] Creating GitHub Release ^& Uploading .exe...
echo ====================================================================
gh release create %VERSION% dist\PulseRemote.exe --title "Pulse Remote %VERSION%" --notes "%NOTES%"
if errorlevel 1 (
    echo.
    echo [ERROR] GitHub release upload failed.
    echo Check if tag '%VERSION%' already exists or check your internet connection.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo                  🎉 UPDATE PUBLISHED SUCCESSFULLY!
echo ====================================================================
echo.
echo 1. GitHub Release Created: https://github.com/khushal-jangid/pulse-remote-pc/releases/tag/%VERSION%
echo 2. Live Website:           https://khushal-jangid.github.io/pulse-remote-pc/
echo.
echo The website download button will now automatically serve %VERSION%!
echo ====================================================================
echo.
pause
