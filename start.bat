@echo off
title HydraCure - Smart Water Quality Monitoring System
cls

echo ========================================================
echo     HydraCure - Smart Water Quality Monitoring System
echo ========================================================
echo.

:: 1. Launch ML Inference Bridge in background
echo [1/3] Starting ML Inference Engine...
if exist ".venv\Scripts\python.exe" (
    start "HydraCure ML Bridge" /B ".venv\Scripts\python.exe" inference_bridge.py
) else (
    start "HydraCure ML Bridge" /B python inference_bridge.py
)
echo      - ML Inference Engine active in background.
echo      - If it reports missing packages, run:
echo        pip install joblib scikit-learn pandas numpy firebase-admin
echo.

:: 2. Start Node.js Web Server
echo [2/3] Starting HydraCure HTTP Server on Port 8000...
echo.

:: 3. Open Web Dashboard once the server is listening
echo [3/3] Dashboard will open at http://localhost:8000 in a moment...
start /B cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
echo.
echo ========================================================
echo   Application is Live! Keep this window open.
echo   Press Ctrl+C to stop the application.
echo   Or run stop.bat from another window.
echo ========================================================
echo.

node server.js
