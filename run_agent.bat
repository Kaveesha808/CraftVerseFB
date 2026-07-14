@echo off
echo ========================================================
echo  Starting CraftReel AI Agent - FB Reels Automation System
echo ========================================================
echo Cleaning up any previous server instances on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a 2>nul
cd /d "%~dp0"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
