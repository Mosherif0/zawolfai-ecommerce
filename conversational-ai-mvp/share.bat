@echo off
REM Builds a clean, share-safe ZIP of this project (your .env is excluded and secrets are scanned).
setlocal
cd /d "%~dp0"
python "%~dp0tools\build_share_zip.py" %*
echo.
pause
endlocal