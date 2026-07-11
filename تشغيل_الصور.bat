@echo off
title Image Generator - مولد الصور
cd /d C:\autosystem
echo تشغيل مولد الصور على http://127.0.0.1:5002
start "" http://127.0.0.1:5002
python image_generator\server.py
pause
