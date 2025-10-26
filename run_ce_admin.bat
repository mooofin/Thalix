@echo off
REM Launch Cheat Engine as Administrator with the Dark Souls cheat table
echo Launching Cheat Engine as Administrator...
echo.
echo This will open Cheat Engine with elevated privileges
echo so it can attach to Dark Souls Remastered.
echo.

set CE_PATH=C:\Program Files\Cheat Engine 7.5\cheatengine-x86_64.exe
set CT_PATH=C:\Users\SIDDHARTH U\Downloads\1FRDarkSoulsRemastered.CT

if not exist "%CE_PATH%" (
    echo ERROR: Cheat Engine not found at:
    echo %CE_PATH%
    echo.
    echo Please update CE_PATH in this script.
    pause
    exit /b 1
)

if not exist "%CT_PATH%" (
    echo WARNING: Cheat table not found at:
    echo %CT_PATH%
    echo.
    echo Launching CE without table...
    echo.
    powershell -Command "Start-Process '%CE_PATH%' -Verb RunAs"
) else (
    echo Opening: %CT_PATH%
    echo.
    powershell -Command "Start-Process '%CE_PATH%' -ArgumentList '%CT_PATH%' -Verb RunAs"
)

echo.
echo Cheat Engine should now open with administrator privileges.
echo.
pause
