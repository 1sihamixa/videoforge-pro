@echo off
:: ══════════════════════════════════════════════
::  Watchdog — يراقب السيرفر ويعيد تشغيله
::  إذا توقف لأي سبب (كهرباء، خطأ، إلخ)
:: ══════════════════════════════════════════════

cd /d "C:\autosystem"

:WATCH_LOOP
timeout /t 30 /nobreak > nul

:: تحقق من أن السيرفر يرد
curl -s --max-time 5 http://127.0.0.1:5000/health > nul 2>&1

if errorlevel 1 (
    echo [%date% %time%] ⚠️ السيرفر توقف - جاري إعادة التشغيل... >> workspace\watchdog.log
    
    :: أوقف أي نسخة قديمة
    taskkill /F /FI "WINDOWTITLE eq Flask Server*" > nul 2>&1
    taskkill /F /IM python.exe > nul 2>&1
    timeout /t 3 /nobreak > nul
    
    :: أعد التشغيل
    start "Flask Server" /min cmd /c "python main.py >> workspace\server.log 2>&1"
    
    timeout /t 15 /nobreak > nul
    echo [%date% %time%] ✅ تم إعادة تشغيل السيرفر >> workspace\watchdog.log
) else (
    echo [%date% %time%] ✅ السيرفر يعمل >> workspace\watchdog.log
)

goto WATCH_LOOP
