@echo off
rem Starts Forward Check and opens it in the browser. Close this window to stop the server.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
