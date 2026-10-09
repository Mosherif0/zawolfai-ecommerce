@echo off
echo ========================================================
echo       Starting CartWise Static Frontend Server...
echo ========================================================
cd /d "%~dp0"
python -m http.server 5173
pause
