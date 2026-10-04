@echo off
REM Launch uvicorn detached with all output to a log file
cd /d "c:\Users\IT\Desktop\conversational-ai-mvp"
start "uvicorn" /b cmd /c "uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug > server_output.log 2>&1"
echo Server launched. Logs: server_output.log

