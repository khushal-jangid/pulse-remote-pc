@echo off
:: =============================================================
::  PulseRemote PC - One-Click Launcher
:: =============================================================
title PulseRemote PC - Phone Controller
cd /d "C:\Users\choya\pc-remote-control"

color 0A
cls
echo.
echo  =============================================================
echo     📱 PULSEREMOTE PC - Phone to PC Remote Controller
echo  =============================================================
echo.
echo  [1/2] Clearing previous server instances...
powershell -Command "Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1

echo  [2/2] Starting PulseRemote PC Engine...
echo.

:: Launch Node Server
start "" node server.js

:: Wait for server initialization
timeout /t 2 /nobreak >nul

:: Open local PC Dashboard with QR Code in default browser
start http://localhost:3000

echo.
echo  =============================================================
echo   ✔ SUCCESS! Server is LIVE!
echo   📱 Scan QR Code or open in Phone: http://10.179.154.111:3000
echo  =============================================================
echo.
