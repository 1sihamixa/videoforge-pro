@echo off
title Wav2Lip - Avatar Server
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Wav2Lip + API - سيرفر الأفيتار الناطق
echo ========================================
echo.

:: Check model
set MODEL_FILE=Wav2Lip\checkpoints\wav2lip_gan.pth
if exist "%MODEL_FILE%" (
    set SIZE=%~z1 2>nul
    if not defined SIZE set SIZE=0
    for %%f in ("%MODEL_FILE%") do set SIZE=%%~zf
    if !SIZE! GTR 100000000 (
        echo [OK] النموذج المحلي موجود
    ) else (
        echo [!] النموذج غير مكتمل (حجمه صغير)
    )
) else (
    echo [!] النموذج المحلي غير موجود
)
echo.

echo سيتم فتح المتصفح تلقائياً...
echo اضغط Ctrl+C للإيقاف
echo.
timeout /t 3 >nul

:: Kill any existing process on port 5001
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5001" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 1 >nul

start "" http://127.0.0.1:5001
python app_wav2lip.py

pause
