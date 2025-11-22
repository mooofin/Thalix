@echo off
title Thalix - Admin Launcher
echo.
echo ========================================
echo   Starting Thalix as Administrator
echo ========================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with Administrator privileges...
    echo.
    python run_gui.py
) else (
    echo Requesting Administrator privileges...
    echo.
    powershell -Command "Start-Process python -ArgumentList 'run_gui.py' -Verb RunAs -WorkingDirectory '%CD%'"
)

if errorlevel 1 (
    echo.
    echo Error: Failed to start Thalix
    pause
)
