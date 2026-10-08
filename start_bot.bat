@echo off
rem Starts the Forward Check Telegram bot. Close this window to stop it.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m bot.telegram_bot
pause
