@echo off
title HydraCure - Stop Application Services
cls

echo ========================================================
echo         Stopping HydraCure Application Services        
echo ========================================================
echo.

echo [1/2] Stopping Node.js Web Server (Port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo      - Web server stopped.

echo [2/2] Stopping Python ML Inference Engine...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*inference_bridge.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo      - ML Inference Engine stopped.

echo.
echo ========================================================
echo   All HydraCure services have been safely stopped.
echo ========================================================
echo.
timeout /t 3 >nul
