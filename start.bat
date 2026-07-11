@echo off
title VideoForge Pro - Wav2Lip Avatar Server
echo ==============================================
echo   VideoForge Pro v2.0
echo   Wav2Lip Talking Avatar Generator
echo ==============================================
echo.
echo [1/3] التحقق من المتطلبات...
pip install -r requirements.txt > nul 2>&1
echo [2/3] بدء تشغيل الخادم...
echo.
echo الخادم سيعمل على: http://127.0.0.1:5000
echo لوحة التحكم: http://127.0.0.1:5000/admin
echo.
echo اضغط Ctrl+C للإيقاف
echo ==============================================
python run.py --port 5000
pause
