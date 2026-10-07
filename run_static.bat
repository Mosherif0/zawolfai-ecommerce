@echo off
echo ========================================================
echo       Starting CartWise Static Frontend Server...
echo ========================================================
cd /d "%~dp0"
if exist "C:\Users\ASUS\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    "C:\Users\ASUS\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m http.server 8000
) else (
    python -m http.server 8000
)
pause
