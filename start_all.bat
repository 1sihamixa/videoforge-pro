@echo off
title تشغيل جميع المشاريع
chcp 65001 >nul
cd /d C:\autosystem

echo =============================================
echo   تشغيل جميع المشاريع
echo =============================================
echo.

:: أفتح لوحة التحكم
start "" "C:\autosystem\index.html"

:: 1. Wav2Lip Avatar - Port 5003
echo [1/4] تشغيل Wav2Lip Avatar... (port 5003)
start "Wav2Lip Avatar" /B python wav2lip_avatar\app.py > wav2lip_avatar\server.log 2>&1
timeout /t 3 >nul

:: 2. Image Generator - Port 5002
echo [2/4] تشغيل مولد الصور... (port 5002)
start "Image Generator" /B python image_generator\server.py > image_generator\server.log 2>&1
timeout /t 3 >nul

:: 3. Perfume Store - Port 5004
echo [3/4] تشغيل متجر العطور... (port 5004)
start "Perfume Store" /B python aya_parfum\app.py > aya_parfum\server.log 2>&1
timeout /t 3 >nul

:: 4. Video Factory - Port 5005
echo [4/4] تشغيل مصنع الفيديو... (port 5005)
start "Video Factory" /B python video_factory\server.py > video_factory\server.log 2>&1
timeout /t 2 >nul

echo.
echo =============================================
echo   جميع المشاريع شغالة!
echo   Wav2Lip Avatar: http://127.0.0.1:5003
echo   مولد الصور:     http://127.0.0.1:5002
echo   متجر العطور:    http://127.0.0.1:5004
echo   مصنع الفيديو:   http://127.0.0.1:5005
echo =============================================
echo.
echo اضغط Ctrl+C للإيقاف
echo.

:: ابق النافذة مفتوحة
pause >nul

:: عند الإغلاق، أوقف كل السيرفرات
echo إيقاف جميع السيرفرات...
taskkill /f /fi "WINDOWTITLE eq Wav2Lip Avatar" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Image Generator" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Perfume Store" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq Video Factory" >nul 2>&1
echo تم.
pause
