@echo off
title YouTube Producer Pro v2.0
chcp 65001 >nul

echo ============================================
echo  📹 YouTube Producer Pro v2.0
echo ============================================
echo.
echo  [1] 🖥  الواجهة الرسومية
echo  [2] 📝  إنتاج فيديو واحد
echo  [3] 📦  إنتاج دفعة
echo  [4] 📋  إنتاج من Google Sheet
echo  [5] 🔧  الإعدادات
echo  [6] 🌐  تشغيل الخادم (لـ n8n)
echo  [7] ❌  خروج
echo.

set /p choice="  اختر رقم (1-7): "

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto single
if "%choice%"=="3" goto batch
if "%choice%"=="4" goto sheet
if "%choice%"=="5" goto setup
if "%choice%"=="6" goto server
if "%choice%"=="7" exit /b

:gui
start pythonw -m youtube_producer --gui
exit /b

:single
set /p topic="  موضوع الفيديو: "
python -m youtube_producer --topic "%topic%"
pause
exit /b

:batch
python -m youtube_producer --batch
pause
exit /b

:sheet
python -m youtube_producer --sheet
pause
exit /b

:setup
python -m youtube_producer --setup
pause
exit /b

:server
start pythonw -m youtube_producer --server
echo  ✅ الخادم يعمل على http://localhost:5000
pause
exit /b
