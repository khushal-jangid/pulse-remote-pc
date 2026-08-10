@echo off
title PulseRemote PC - 1-Click Update Publisher
cd /d "%~dp0"
python publish_update.py
pause
