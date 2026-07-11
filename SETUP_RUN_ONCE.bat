@echo off
:: ══════════════════════════════════════════════
::  إعداد النظام — شغّله مرة واحدة فقط
::  سيجعل كل شيء يعمل تلقائياً للأبد
:: ══════════════════════════════════════════════

title إعداد النظام التلقائي
color 0B

echo.
echo ╔══════════════════════════════════════╗
echo ║      إعداد النظام التلقائي          ║
echo ║      شغّله مرة واحدة فقط!           ║
echo ╚══════════════════════════════════════╝
echo.

:: [1] تأكد من وجود المجلدات
echo [1/6] إنشاء المجلدات...
mkdir "C:\Users\HP\server_files" 2>nul
mkdir "C:\Users\HP\server_files\audio" 2>nul
mkdir "C:\Users\HP\server_files\videos" 2>nul
mkdir "C:\Users\HP\server_files\subtitles" 2>nul
mkdir "C:\Users\HP\server_files\exports" 2>nul
mkdir "C:\Users\HP\server_files\bg_videos" 2>nul
mkdir "C:\Users\HP\server_files\thumbnails" 2>nul
mkdir "C:\Users\HP\server_files\music" 2>nul
mkdir "C:\Users\HP\server_files\sfx" 2>nul
echo    ✅ تم

:: [2] نسخ ملفات النظام
echo [2/6] نسخ ملفات النظام...
copy /Y "%~dp0watchdog.bat" "C:\Users\HP\server_files\watchdog.bat" > nul
copy /Y "%~dp0server.py" "C:\autosystem\server.py" > nul
echo    ✅ تم

:: [3] تثبيت المكتبات المطلوبة
echo [3/6] تثبيت المكتبات...
pip install flask gtts pillow openai-whisper requests edge-tts aiohttp --quiet
echo    ✅ تم

:: [4] إضافة للـ Windows Startup (يشتغل مع Windows)
echo [4/6] إضافة للتشغيل التلقائي مع Windows...
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
copy /Y "%~dp0autostart.bat" "%STARTUP_DIR%\FlaskAutoStart.bat" > nul
echo    ✅ تم - سيشتغل تلقائياً مع كل إعادة تشغيل

:: [5] إنشاء اختصار على سطح المكتب
echo [5/6] إنشاء اختصار على سطح المكتب...
set DESKTOP=%USERPROFILE%\Desktop
copy /Y "%~dp0autostart.bat" "%DESKTOP%\🚀 تشغيل السيرفر.bat" > nul
echo    ✅ تم

:: [6] تشغيل النظام الآن فوراً
echo [6/6] تشغيل النظام الآن...
start "" "%~dp0autostart.bat"
echo    ✅ تم

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  ✅ الإعداد اكتمل بنجاح!                   ║
echo ║                                              ║
echo ║  الآن:                                       ║
echo ║  • السيرفر يعمل تلقائياً مع Windows         ║
echo ║  • Watchdog يراقبه ويعيد تشغيله إذا وقف     ║
echo ║  • اختصار على سطح المكتب للتشغيل اليدوي    ║
echo ║                                              ║
echo ║  لا تحتاج لفعل أي شيء آخر! ✨              ║
echo ╚══════════════════════════════════════════════╝
echo.
pause
