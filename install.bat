@echo off
:: MotionAI Windows Quick Install Script
:: Double-click this to set up your environment

echo ============================================
echo    MotionAI - Quick Install Script
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please download Python 3.11 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found.
echo.

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.

:: Install requirements
echo Installing dependencies (this may take 5-10 minutes)...
echo.
pip install -r requirements.txt

:: Check if PyAudio installed (may need special handling)
python -c "import pyaudio" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [INFO] PyAudio failed. Trying pipwin...
    pip install pipwin --quiet
    pipwin install pyaudio
)

echo.
echo ============================================
echo    Installation Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Edit core\config.py with your API keys
echo 2. Run: python main.py
echo.
echo Or build the .exe:
echo    pyinstaller MotionAI.spec
echo.
pause