@echo off
REM Guitar Transcription Web App - Quick Start Script (Windows)

setlocal enabledelayedexpansion

echo.
echo 🎸 Guitar Transcription Web App - Setup Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python not found. Please install Python 3.10+
    exit /b 1
)
echo ✓ Python found
python --version

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Node.js not found. Please install Node.js 16+
    exit /b 1
)
echo ✓ Node.js found
node --version

echo.
echo Setting up backend...

cd backend

if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
echo ✓ Python dependencies installed

REM Create directories
if not exist "models" mkdir models
if not exist "uploads" mkdir uploads
if not exist "temp" mkdir temp
echo ✓ Created model and upload directories

cd ..

echo.
echo Setting up frontend...

cd frontend

REM Install npm dependencies
echo Installing npm dependencies...
npm install
echo ✓ npm dependencies installed

cd ..

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo Terminal 1 - Start Backend:
echo   cd backend
echo   venv\Scripts\activate
echo   python -m uvicorn main:app --reload
echo.
echo Terminal 2 - Start Frontend:
echo   cd frontend
echo   npm run dev
echo.
echo Then open: http://localhost:5173
echo.
echo For more information:
echo   - README.md (full documentation)
echo   - SETUP_GUIDE.md (detailed setup)
echo   - QUICK_REFERENCE.md (quick commands)
echo.
echo Happy transcribing! 🎸
echo.
