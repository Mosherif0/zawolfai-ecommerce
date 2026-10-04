@echo off  
taskkill /f /im uvicorn.exe 2>nul  
taskkill /f /im python.exe /fi \"WINDOWTITLE eq Conversational^\" 2>nul  
echo done  
