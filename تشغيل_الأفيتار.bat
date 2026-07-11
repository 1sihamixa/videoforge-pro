@echo off
title Wav2Lip Avatar - سيرفر الأفيتار
cd /d C:\autosystem
echo تشغيل Wav2Lip Avatar على http://127.0.0.1:5003
start "" http://127.0.0.1:5003
python wav2lip_avatar\app.py
pause
