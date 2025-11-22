"""
Build script for creating Thalix executable
Uses PyInstaller to create a standalone executable
"""

import os
import sys
import subprocess
import shutil

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("PyInstaller already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing PyInstaller: {e}")
            return False

def create_spec_file():
    """Create PyInstaller spec file for the application"""
    spec_content = '''

block_cipher = None

a = Analysis(
    ['src/thalix_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'psutil',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Thalix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico',
)
'''
    
    with open('elden_ring_gui.spec', 'w') as f:
        f.write(spec_content)
    print("Created PyInstaller spec file")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building Thalix executable...")
    
    try:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name=Thalix",
            "--icon=assets/app_icon.ico",
            "--add-data=assets;assets",
            "--add-data=requirements.txt;.",
            "--hidden-import=customtkinter",
            "--hidden-import=psutil",
            "--hidden-import=PIL",
            "--hidden-import=PIL.Image",
            "--hidden-import=PIL.ImageTk",
            "src/thalix_gui.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(" Executable built successfully!")
            print(" Output: dist/Thalix.exe")
            return True
        else:
            print(" Error building executable:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f" Error during build: {e}")
        return False

def create_installer_script():
    """Create a simple installer script"""
    installer_content = '''@echo off
title Thalix Installer
echo.
echo ========================================
echo   Thalix Installer
echo ========================================
echo.

echo Installing Thalix...
echo.

REM Create desktop shortcut
set "desktop=%USERPROFILE%\\Desktop"
set "exe_path=%~dp0dist\\Thalix.exe"

if exist "%exe_path%" (
    echo Creating desktop shortcut...
    powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%desktop%\\Thalix.lnk'); $Shortcut.TargetPath = '%exe_path%'; $Shortcut.Save()"
    echo.
    echo  Installation complete!
    echo  Desktop shortcut created
    echo.
    echo To run: Double-click "Thalix" on your desktop
    echo.
    echo   IMPORTANT: Right-click and "Run as administrator" for full functionality
    echo.
) else (
    echo  Executable not found. Please run build_exe.py first.
)

pause
'''
    
    with open('install.bat', 'w') as f:
        f.write(installer_content)
    print("Created installer script: install.bat")

def main():
    """Main build process"""
    print("=" * 50)
    print("THALIX - EXECUTABLE BUILDER")
    print("=" * 50)
    print()
    
    if not os.path.exists("assets"):
        print(" Assets folder not found!")
        print("Please make sure you have the assets folder with your images.")
        return
    
    if not install_pyinstaller():
        print(" Could not install PyInstaller")
        return
    
    create_spec_file()
    
    if build_executable():
        print()
        print(" Build completed successfully!")
        print()
        print(" Files created:")
        print("   - dist/Thalix.exe (Main executable)")
        print("   - install.bat (Installer script)")
        print()
        print(" To install:")
        print("   1. Run install.bat to create desktop shortcut")
        print("   2. Right-click the shortcut and 'Run as administrator'")
        print()
        print("  Note: The executable includes all assets and dependencies")
        print("   No additional installation required!")
        
        create_installer_script()
        
    else:
        print(" Build failed. Check the error messages above.")

if __name__ == "__main__":
    main()
