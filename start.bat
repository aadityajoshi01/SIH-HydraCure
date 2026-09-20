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
echo.

:: 2. Open Web Dashboard in default browser
echo [2/3] Launching HydraCure Web Dashboard...
timeout /t 2 /nobreak >nul
start http://localhost:8000
echo      - Dashboard available at: http://localhost:8000
echo.

:: 3. Start Node.js Web Server
echo [3/3] Starting HydraCure HTTP Server on Port 8000...
echo.
echo ========================================================
echo   Application is Live! Keep this window open.
echo   Press Ctrl+C to stop the application.
echo ========================================================
echo.

node server.js
