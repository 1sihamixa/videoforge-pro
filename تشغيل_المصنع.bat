@echo off
title Video Factory - مصنع الفيديو
cd /d C:\autosystem\video_factory
echo تشغيل مصنع الفيديو على http://127.0.0.1:5005
start "" http://127.0.0.1:5005
set PORT=5005
python server.py
pause
