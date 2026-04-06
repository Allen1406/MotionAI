@echo off
:: MotionAI - Build Windows .exe
:: Run after installing requirements

echo ============================================
echo    MotionAI - Building Windows .exe
echo ============================================
echo.

:: Verify PyInstaller
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller==6.3.0
)

echo.
echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Done.
echo.

echo [2/3] Building MotionAI.exe...
echo This will take 3-8 minutes. Please wait.
echo.
pyinstaller MotionAI.spec

echo.
if exist "dist\MotionAI\MotionAI.exe" (
    echo [3/3] BUILD SUCCESSFUL!
    echo.
    echo Output: dist\MotionAI\MotionAI.exe
    echo.
    echo To run: double-click dist\MotionAI\MotionAI.exe
    echo To share: zip the entire dist\MotionAI\ folder
    echo.
    
    :: Ask to launch
    set /p launch="Launch MotionAI now? (y/n): "
    if /i "%launch%"=="y" (
        start "" "dist\MotionAI\MotionAI.exe"
    )
) else (
    echo [ERROR] Build failed. Check the output above for errors.
    echo.
    echo Common fixes:
    echo - Run: pip install --upgrade pyinstaller
    echo - Check that all packages in requirements.txt are installed
    echo - Try running: python main.py first to check for errors
)

echo.
pause