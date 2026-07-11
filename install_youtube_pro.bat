@echo off
:: ============================================================
::  YouTube Producer Pro - Installer
::  التنصيب الآلي على أي حاسوب Windows
:: ============================================================
title YouTube Producer Pro - تنصيب

echo.
echo ============================================
echo   YouTube Producer Pro - التنصيب الآلي
echo ============================================
echo.

:: 1. التحقق من صلاحية Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] يجب تشغيل هذا المثبت كـ Administrator
    echo     اضغط كlick يمين ^> Run as Administrator
    pause
    exit /b 1
)
echo [OK] صلاحية Administrator

:: 2. تحديد مسار التثبيت
set "INSTALL_DIR=C:\YouTubePro"
echo [*] مسار التثبيت: %INSTALL_DIR%

:: 3. إنشاء المجلدات
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\workspace" mkdir "%INSTALL_DIR%\workspace"
for %%d in (audio videos subtitles exports bg_videos thumbnails music logs) do (
    if not exist "%INSTALL_DIR%\workspace\%%d" mkdir "%INSTALL_DIR%\workspace\%%d"
)
echo [OK] المجلدات جاهزة

:: 4. نسخ الملفات
echo [*] نسخ الملفات...
copy /Y "%~dp0youtube_producer.py" "%INSTALL_DIR%\youtube_producer.py" >nul 2>&1
echo [OK] الملفات منسوخة

:: 5. التحقق من Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Python غير مثبت - سيتم تحميله...
    echo     تحميل Python 3.11 من الموقع الرسمي...
    start https://www.python.org/downloads/
    echo.
    echo     بعد تثبيت Python، شغل المثبّت مرة أخرى.
    pause
    exit /b 1
)

:: 6. تثبيت المكتبات المطلوبة
echo [*] تثبيت مكتبات Python المطلوبة...
python -m pip install --upgrade pip -q
python -m pip install flask gtts pillow requests edge-tts aiohttp -q
echo [OK] المكتبات مثبتة

:: 7. التحقق من FFmpeg
where ffmpeg >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] FFmpeg غير موجود في PATH
    echo     سيتم تحميله وتثبيته تلقائياً...
    
    :: تحميل FFmpeg
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TEMP%\ffmpeg.zip'}"
    powershell -Command "& {Expand-Archive -Path '%TEMP%\ffmpeg.zip' -DestinationPath 'C:\ffmpeg' -Force}"
    
    :: إضافة إلى PATH
    setx PATH "%PATH%;C:\ffmpeg\bin" /M >nul
    echo [OK] FFmpeg مثبت في C:\ffmpeg
) else (
    echo [OK] FFmpeg موجود
)

:: 8. إنشاء اختصار سطح المكتب
echo [*] إنشاء اختصار سطح المكتب...
powershell -Command "& {$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\YouTube Pro.lnk'); $SC.TargetPath = 'cmd.exe'; $SC.Arguments = '/k cd /d %INSTALL_DIR% ^&^& python youtube_producer.py --server ^&^& pause'; $SC.WorkingDirectory = '%INSTALL_DIR%'; $SC.Description = 'YouTube Producer Pro'; $SC.Save()}"
echo [OK] اختصار سطح المكتب جاهز

:: 9. إنشاء اختصار التشغيل التلقائي
echo [*] إنشاء التشغيل التلقائي مع Windows...
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -Command "& {$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%STARTUP_DIR%\YouTube Pro Server.lnk'); $SC.TargetPath = 'cmd.exe'; $SC.Arguments = '/c cd /d %INSTALL_DIR% ^&^& python youtube_producer.py --server'; $SC.WorkingDirectory = '%INSTALL_DIR%'; $SC.Description = 'YouTube Pro Server - يبدأ مع Windows'; $SC.WindowStyle = 7; $SC.Save()}"
echo [OK] التشغيل التلقائي مع Windows

:: 10. تهيئة ملف المحتوى التجريبي
cd /d "%INSTALL_DIR%"
python youtube_producer.py --init >nul 2>&1
echo [OK] ملف المحتوى التجريبي جاهز

:: 11. عرض معلومات Pexels
echo.
echo ============================================
echo   التنصيب اكتمل بنجاح! 
echo ============================================
echo.
echo   🔑 مهم: احصل على مفتاح Pexels API المجاني:
echo      1. افتح: https://www.pexels.com/api/
echo      2. سجل حساب مجاني
echo      3. انسخ المفتاح
echo.
echo   📝 ضع المفتاح في ملف:
echo      %INSTALL_DIR%\youtube_producer.py
echo      (ابحث عن: YOUR_PEXELS_API_KEY)
echo.
echo   🚀 طرق الاستخدام:
echo      فيديو واحد:  python youtube_producer.py --topic "موضوعك"
echo      دفعة:        python youtube_producer.py --batch
echo      خادم API:    python youtube_producer.py --server
echo.
echo   ✅ البرنامج يشتغل تلقائياً مع Windows
echo   ✅ اختصار على سطح المكتب للتشغيل اليدوي
echo.
pause
