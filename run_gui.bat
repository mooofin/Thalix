@echo off
title Elden Ring Stutter Fix GUI
echo.
echo Elden Ring Stutter Fix GUI
echo =============================
echo.
echo Starting the application...
echo.

python run_gui.py

if errorlevel 1 (
    echo.
    echo Error running the application
    echo Make sure you have installed the requirements:
    echo    pip install -r requirements.txt
    echo.
    pause
)
