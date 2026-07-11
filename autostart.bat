@echo off
:: ══════════════════════════════════════════════
::  نظام التشغيل التلقائي — يعمل عند بدء Windows
::  لا تحتاج لفعل أي شيء، كل شيء يشتغل وحده
:: ══════════════════════════════════════════════

title Content Factory Pro - جاري التشغيل...
color 0A
cd /d "C:\autosystem"

:: انتظر 15 ثانية حتى يكتمل تحميل Windows
timeout /t 15 /nobreak > nul

echo.
echo ╔══════════════════════════════════════╗
echo ║   Content Factory Pro v3.0          ║
echo ║    يعمل 24/7 بدون توقف              ║
echo ╚══════════════════════════════════════╝
echo.

:: تشغيل السيرفر في خلفية منفصلة
echo [%time%] تشغيل الخادم...
start "Flask Server" /min cmd /c "python main.py >> workspace\server.log 2>&1"

:: انتظر السيرفر يبدأ
timeout /t 8 /nobreak > nul

:: تحقق أن السيرفر يعمل
:CHECK_SERVER
curl -s http://127.0.0.1:5000/health > nul 2>&1
if errorlevel 1 (
    echo [%time%] السيرفر لم يبدأ بعد، انتظار...
    timeout /t 3 /nobreak > nul
    goto CHECK_SERVER
)

echo [%time%] ✅ الخادم يعمل على port 5000

:: تشغيل مراقب السيرفر (يعيد تشغيله إذا توقف)
start "Server Watchdog" /min cmd /c "C:\autosystem\watchdog.bat"

echo [%time%] ✅ Watchdog يعمل
echo.
echo ══════════════════════════════════════
echo   النظام يعمل بشكل كامل ✅
echo   http://localhost:5000
echo ══════════════════════════════════════
echo.

:: أبقِ النافذة مفتوحة لمراقبة الـ logs
echo [معلومات] الـ logs محفوظة في:
echo   C:\autosystem\workspace\server.log
echo.
echo اضغط أي زر لإغلاق هذه النافذة (السيرفر سيستمر في العمل)
pause > nul
