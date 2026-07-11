@echo off
title Wav2Lip Video Creator
chcp 65001 >nul

echo ========================================
echo   Wav2Lip - صانع الفيديوهات الناطقة
echo ========================================
echo.

:: Check if model exists
if exist "Wav2Lip\checkpoints\wav2lip_gan.pth" (
    set size=%~z1
    if !size! GTR 100000000 (
        echo ✅ النموذج المحلي موجود
    ) else (
        echo ⏳ النموذج لم يكتمل تحميله
    )
) else (
    echo ⏳ النموذج المحلي غير موجود
)
echo.

echo اختر طريقة التشغيل:
echo ====================
echo 1. واجهة ويب (Web Interface)
echo 2. سطر أوامر (CLI)
echo 3. تحميل النموذج (Download Model)
echo.
set /p choice="اختيار (1-3): "

if "%choice%"=="1" (
    echo.
    echo بدء تشغيل الواجهة الرسومية...
    echo افتح المتصفح على: http://127.0.0.1:5001
    echo.
    python app_wav2lip.py
) else if "%choice%"=="2" (
    echo.
    echo طريقة الاستخدام:
    echo python talking_avatar.py <صورة> <صوت> <فيديو>
    echo.
    echo مثال:
    echo python talking_avatar.py face.jpg voice.mp3 output.mp4
    echo.
    echo أو مع Gradio API المجاني:
    echo python talking_avatar.py face.jpg voice.mp3 output.mp4 --gradio
    echo.
    pause
) else if "%choice%"=="3" (
    echo.
    echo تحميل نموذج Wav2Lip...
    python download_wav2lip.py
    pause
) else (
    echo اختيار غير صحيح
    pause
)
