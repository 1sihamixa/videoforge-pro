@echo off
title YouTube Producer Pro - Installation
chcp 65001 >nul

setlocal enabledelayedexpansion

echo ============================================
echo  📹 YouTube Producer Pro v2.0
echo  التثبيت الكامل
echo ============================================
echo.

:: المسارات
set "APP_DIR=C:\Program Files\YouTube Producer Pro"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\YouTube Producer Pro"
set "SRC_DIR=C:\autosystem"

echo [1/5] التحقق من المتطلبات...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [خطأ] Python غير موجود!
    echo قم بتحميله من: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo    ✅ Python %PY_VER%

ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo    ⚠️ FFmpeg غير موجود - ثبته من: https://ffmpeg.org/download.html
) else (
    echo    ✅ FFmpeg موجود
)

echo.
echo [2/5] تثبيت المكتبات المطلوبة...
pip install --upgrade pip -q 2>nul
pip install gtts edge-tts flask pillow requests pyttsx3 -q
echo    ✅ المكتبات مثبتة

echo.
echo [3/5] إنشاء اختصارات سطح المكتب...
:: حذف الاختصارات القديمة
if exist "%DESKTOP_DIR%\YouTube Producer.lnk" del "%DESKTOP_DIR%\YouTube Producer.lnk"
if exist "%DESKTOP_DIR%\YouTube Producer (CLI).lnk" del "%DESKTOP_DIR%\YouTube Producer (CLI).lnk"

:: اختصار الواجهة الرسومية (VBS)
powershell -Command ^
    "$WS = New-Object -ComObject WScript.Shell; " ^
    "$SC = $WS.CreateShortcut('%DESKTOP_DIR%\YouTube Producer.lnk'); " ^
    "$SC.TargetPath = 'wscript.exe'; " ^
    "$SC.Arguments = '%SRC_DIR%\YouTube Producer.vbs'; " ^
    "$SC.WorkingDirectory = '%SRC_DIR%\youtube_workspace'; " ^
    "$SC.Description = 'YouTube Producer Pro v2.0'; " ^
    "$SC.IconLocation = '%SystemRoot%\System32\SHELL32.dll,167'; " ^
    "$SC.Save()"
echo    ✅ اختصار الواجهة الرسومية (سطح المكتب)

:: اختصار CLI
powershell -Command ^
    "$WS = New-Object -ComObject WScript.Shell; " ^
    "$SC = $WS.CreateShortcut('%DESKTOP_DIR%\YouTube Producer (CLI).lnk'); " ^
    "$SC.TargetPath = '%SRC_DIR%\YouTube Producer.bat'; " ^
    "$SC.WorkingDirectory = '%SRC_DIR%\youtube_workspace'; " ^
    "$SC.Description = 'YouTube Producer Pro CLI'; " ^
    "$SC.IconLocation = '%SystemRoot%\System32\SHELL32.dll,166'; " ^
    "$SC.Save()"
echo    ✅ اختصار CLI (سطح المكتب)

echo.
echo [4/5] إنشاء اختصارات Start Menu...
if not exist "%START_MENU%" mkdir "%START_MENU%"

powershell -Command ^
    "$WS = New-Object -ComObject WScript.Shell; " ^
    "$SC = $WS.CreateShortcut('%START_MENU%\YouTube Producer.lnk'); " ^
    "$SC.TargetPath = 'wscript.exe'; " ^
    "$SC.Arguments = '%SRC_DIR%\YouTube Producer.vbs'; " ^
    "$SC.WorkingDirectory = '%SRC_DIR%\youtube_workspace'; " ^
    "$SC.Save()"
echo    ✅ اختصار Start Menu

echo.
echo [5/5] (اختياري) التشغيل التلقائي مع Windows...
echo    هل تريد تشغيل الخادم تلقائياً مع Windows؟
set /p autostart="  (y/n, default n): "
if /i "%autostart%"=="y" (
    if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"
    powershell -Command ^
        "$WS = New-Object -ComObject WScript.Shell; " ^
        "$SC = $WS.CreateShortcut('%STARTUP_DIR%\YouTube Producer Server.lnk'); " ^
        "$SC.TargetPath = 'pythonw.exe'; " ^
        "$SC.Arguments = '-m youtube_producer --server'; " ^
        "$SC.WorkingDirectory = '%SRC_DIR%'; " ^
        "$SC.Description = 'YouTube Producer Server'; " ^
        "$SC.IconLocation = '%SystemRoot%\System32\SHELL32.dll,170'; " ^
        "$SC.Save()"
    echo    ✅ التشغيل التلقائي مفعل
) else (
    echo    ✅ تم تخطي التشغيل التلقائي
)

echo.
echo ============================================
echo  ✅ تم التثبيت بنجاح!
echo ============================================
echo.
echo  ▶️  انقر نقراً مزدوجاً على: 
echo     📁 سطح المكتب → "YouTube Producer"
echo.
echo  ▶️  أو استخدم سطر الأوامر:
echo     python -m youtube_producer --help
echo.
echo  ▶️  أول مرة؟ شغّل الإعدادات أولاً:
echo     python -m youtube_producer --setup
echo.
echo ============================================
pause
