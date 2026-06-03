@echo off
:: ─────────────────────────────────────────────────────────
::  STEM::EXTRACT  ·  Windows Launcher
:: ─────────────────────────────────────────────────────────

set PORT=5000
if not "%1"=="" set PORT=%1

echo.
echo   ╔══ STEM::EXTRACT ══════════════════════════════╗
echo   ║   Audio Source Separation — Demucs Engine     ║
echo   ╚════════════════════════════════════════════════╝
echo.

:: Create venv if missing
if not exist "venv\" (
    echo   ^→ Creating virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate.bat

:: Install deps
echo   ^→ Checking dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

:: Check ffmpeg
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo   WARNING: ffmpeg not found.
    echo   Install from https://ffmpeg.org or via:  winget install ffmpeg
    echo.
)

echo.
echo   ^→ Starting server on http://localhost:%PORT%
echo   ^→ Press Ctrl+C to stop
echo.

python app.py %PORT%

pause
