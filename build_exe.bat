@echo off
setlocal
echo ============================================
echo   Building PDF Merger (app folder + installer)
echo ============================================
echo.

REM --- Check Python is installed ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this machine.
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/4] Installing required packages...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install packages. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous build folders (if any)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

if not exist fonts (
    echo.
    echo   NOTE: The 'fonts' folder was not found - Arabic fonts will NOT be bundled.
    echo.
)

echo.
echo [3/4] Building the app folder (dist\PDFMerger) ...
python -m PyInstaller --noconfirm PDFMerger.spec
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Building the installer ...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo   Inno Setup 6 was not found, so only the app folder was built.
    echo   Install it with:  winget install JRSoftware.InnoSetup
    echo   then run this script again to get the installer.
    echo.
    echo The app is ready at: dist\PDFMerger\PDFMerger.exe
    pause
    exit /b 0
)
"%ISCC%" /Q installer.iss
if errorlevel 1 (
    echo [ERROR] Installer build failed.
    pause
    exit /b 1
)

echo.
echo Done!
echo   Installer: installer_output\PDFMerger-Setup-11.0.0.exe
echo   App folder: dist\PDFMerger\PDFMerger.exe
echo.
pause
