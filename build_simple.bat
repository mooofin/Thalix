@echo off
title Elden Ring Stutter Fix - Build Executable
echo.
echo ========================================
echo   Elden Ring Stutter Fix Builder
echo ========================================
echo.

echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building executable...
echo.

pyinstaller --onefile --windowed --name=EldenRingStutterFix --icon=assets/app_icon.ico --add-data="assets;assets" --hidden-import=customtkinter --hidden-import=psutil --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=PIL.ImageTk src/elden_ring_gui.py

if exist "dist\EldenRingStutterFix.exe" (
    echo.
    echo ✅ Build successful!
    echo 📁 Executable created: dist\EldenRingStutterFix.exe
    echo.
    echo 🚀 To run: Double-click the executable
    echo ⚠️  IMPORTANT: Right-click and "Run as administrator" for full functionality
    echo.
    
    REM Create desktop shortcut
    echo Creating desktop shortcut...
    powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Elden Ring Stutter Fix.lnk'); $Shortcut.TargetPath = '%CD%\dist\EldenRingStutterFix.exe'; $Shortcut.Save()"
    echo ✅ Desktop shortcut created!
    
) else (
    echo.
    echo ❌ Build failed!
    echo Check the error messages above.
)

echo.
pause