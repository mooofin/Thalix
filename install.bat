@echo off
title Thalix Installer
echo.
echo ========================================
echo   Thalix - CPU Affinity Manager
echo ========================================
echo.

echo Installing Thalix...
echo.

REM Create desktop shortcut
set "desktop=%USERPROFILE%\Desktop"
set "exe_path=%~dp0dist\Thalix.exe"

if exist "%exe_path%" (
    echo Creating desktop shortcut...
    powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%desktop%\Thalix.lnk'); $Shortcut.TargetPath = '%exe_path%'; $Shortcut.Save()"
    echo.
    echo Installation complete!
    echo Desktop shortcut created
    echo.
    echo To run: Double-click "Thalix" on your desktop
    echo.
    echo IMPORTANT: Right-click and "Run as administrator" for full functionality
    echo.
) else (
    echo Executable not found. Please run build_exe.py first.
)

pause
