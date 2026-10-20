@echo off
title OpenCut Backend Server
cd /d %~dp0
set PATH=%~dp0ffmpeg;%PATH%
set PYTHONNOUSERSITE=0
set PYTHONPATH=C:\Users\h\AppData\Roaming\Python\Python313\site-packages;%PYTHONPATH%
echo Starting OpenCut Backend Server on port 5679 and Sound Designer on port 5682...
echo Keep this window open while using OpenCut in Premiere.
echo ===================================================
start /b "Sound Designer" C:\Python313\python.exe "%~dp0server\sound_designer_service.py"
%~dp0server\OpenCut-Server.exe
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server exited with code %ERRORLEVEL%.
    pause
)
