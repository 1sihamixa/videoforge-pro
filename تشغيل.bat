@echo off
chcp 65001 >nul
echo ========================================
echo  Talking Avatar Generator
echo  صورة + تسجيل صوتي = فيديو يتكلم
echo ========================================
echo.
echo اختر صورة واسحبها إلى النافذة ثم اضغط Enter:
set /p IMG="> "
echo اختر ملف الصوت واسحبه ثم اضغط Enter:
set /p AUD="> "
echo اسم ملف الفيديو الناتج (مثل: فيديو.mp4):
set /p OUT="> "
echo.
echo اختر المحرك:
echo  1 - Wav2Lip (AI - يحتاج تحميل نموذج)
echo  2 - Gradio (API مجاني - يحتاج انترنت)
echo  3 - Legacy (بدون AI - سريع)
set /p ENG="الرقم (1/2/3): "
if "%ENG%"=="2" goto gradio
if "%ENG%"=="3" goto legacy
python talking_avatar.py "%IMG%" "%AUD%" "%OUT%" --engine wav2lip
goto end
:gradio
python talking_avatar.py "%IMG%" "%AUD%" "%OUT%" --engine wav2lip --gradio
goto end
:legacy
python talking_avatar.py "%IMG%" "%AUD%" "%OUT%" --engine legacy
:end
echo.
pause
