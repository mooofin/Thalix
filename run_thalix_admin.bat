@echo off
echo Starting Thalix with Administrator privileges...
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - Starting Thalix...
    python run_gui.py
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process python -ArgumentList 'run_gui.py' -Verb RunAs -WorkingDirectory '%CD%'"
)

pause
