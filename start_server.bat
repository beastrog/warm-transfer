@echo off
echo Stopping any running FastAPI servers...
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM python3.11.exe >nul 2>&1

echo Starting FastAPI server...
cd backend
start "FastAPI Server" cmd /k "uvicorn main:app --reload --log-level debug"
