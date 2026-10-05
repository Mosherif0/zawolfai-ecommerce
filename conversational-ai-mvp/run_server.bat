@echo off
echo Starting CartWise AI Web Server...
C:\Users\ASUS\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
