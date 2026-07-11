@echo off
title YouTube Producer Pro - Build
chcp 65001 >nul

echo ============================================
echo  بناء YouTube Producer Pro v2.0
echo ============================================
echo.

:: التحقق من Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [خطأ] Python غير موجود!
    pause
    exit /b 1
)

:: التحقق من PyInstaller
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] جاري تثبيت PyInstaller...
    echo.
    echo    ملاحظة: يحتاج اتصال إنترنت
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [خطأ] فشل تثبيت PyInstaller!
        echo.
        echo يمكنك تثبيته يدوياً: pip install pyinstaller
        pause
        exit /b 1
    )
)

echo [*] جاري بناء البرنامج...
echo.

:: حذف البناء السابق
if exist "C:\autosystem\dist" rmdir /s /q "C:\autosystem\dist"
if exist "C:\autosystem\build" rmdir /s /q "C:\autosystem\build"

:: بناء الـ exe
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "YouTube Producer" ^
    --icon "C:\autosystem\youtube_producer\assets\icon.ico" ^
    --add-data "C:\autosystem\youtube_producer\assets;assets" ^
    --hidden-import whisper ^
    --hidden-import edge_tts ^
    --hidden-import gtts ^
    --hidden-import pyttsx3 ^
    --hidden-import flask ^
    --hidden-import PIL._tkinter_finder ^
    --collect-all whisper ^
    --add-data "C:\autosystem\config.json;." ^
    "C:\autosystem\youtube_producer\__main__.py"

if %errorlevel% neq 0 (
    echo.
    echo [خطأ] فشل البناء!
    echo.
    echo قد تحتاج لتثبيت Visual C++ Redistributable:
    echo https://aka.ms/vs/17/release/vc_redist.x64.exe
    pause
    exit /b 1
)

:: إنشاء مجلدات العمل
mkdir "C:\autosystem\dist\youtube_workspace\audio" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\videos" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\subtitles" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\exports" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\bg_videos" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\thumbnails" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\music" >nul 2>&1
mkdir "C:\autosystem\dist\youtube_workspace\logs" >nul 2>&1

echo.
echo ============================================
echo  ✅ البناء اكتمل!
echo ============================================
echo.
echo  الملف: C:\autosystem\dist\YouTube Producer.exe
echo  الحجم:
dir "C:\autosystem\dist\YouTube Producer.exe" 2>nul
echo.
echo  يمكنك الآن تشغيل install.bat كـ Administrator
echo  للتثبيت الكامل مع الاختصارات.
echo.
pause
