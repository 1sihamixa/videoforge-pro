@echo off
cd /d "%~dp0"
echo ========================================
echo  VideoForge Pro - Starting Servers
echo ========================================
echo.

echo [1/2] Starting Main Server (port 5000)...
start "Main Server" python main.py

echo [2/2] Starting Wav2Lip Server (port 5001)...
start "Wav2Lip Server" python app_wav2lip.py

echo.
echo ========================================
echo  Both servers started!
echo  Main:  http://localhost:5000/creator
echo  Wav2Lip: http://localhost:5001
echo ========================================
echo.
pause
