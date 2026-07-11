@echo off
title تثبيت خدمة التشغيل التلقائي
cd /d "%~dp0"

:: 1. منع السكون
echo [1/4] تعطيل وضع السكون...
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /hibernate off

:: 2. إنشاء مهمة في Task Scheduler لتشغيل main.py عند بدء Windows
echo [2/4] إنشاء مهمة التشغيل التلقائي...
schtasks /create /tn "ContentFactoryPro" /tr "cmd /c \"cd /d C:\autosystem && python main.py\"" /sc onstart /delay 0000:30 /ru %USERNAME% /f

:: 3. إنشاء مهمة إعادة تشغيل يومية (يعيد التشغيل كل يوم عند 03:00 صباحاً)
echo [3/4] إنشاء مهمة إعادة التشغيل اليومية...
schtasks /create /tn "ContentFactoryPro_Restart" /tr "cmd /c \"taskkill /f /im python.exe > nul 2>&1 & timeout /t 5 > nul & cd /d C:\autosystem & start /min cmd /c python main.py >> workspace\server.log 2>&1\"" /sc daily /st 03:00 /ru %USERNAME% /f

:: 4. تشغيل السيرفر الآن
echo [4/4] تشغيل السيرفر الآن...
start "ContentFactory" /min cmd /c "python main.py >> workspace\server.log 2>&1"

echo.
echo ✅ تم الإعداد!
echo - السيرفر سيشغل تلقائياً عند بدء تشغيل Windows
echo - السيرفر سيعاد تشغيله يومياً الساعة 03:00 صباحاً
echo - السكون معطل - الحاسوب لن ينام
echo.
echo http://localhost:5000
echo.
pause
