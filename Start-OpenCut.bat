@echo off
setlocal enabledelayedexpansion
title OpenCut Enhanced - Autonomous Video Studio Launcher
cd /d "%~dp0"

echo ===================================================================
echo           OpenCut Enhanced - Autonomous Video Studio
echo ===================================================================
echo.

:: Detect Python executable
set "PYTHON_EXE=python"
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "C:\Python313\python.exe" (
        set "PYTHON_EXE=C:\Python313\python.exe"
    ) else if exist "C:\Python312\python.exe" (
        set "PYTHON_EXE=C:\Python312\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        set "PYTHON_EXE=C:\Python311\python.exe"
    ) else (
        echo [ERROR] Python not found in PATH or standard directories.
        echo Please install Python 3.10+ from python.org and add it to PATH.
        pause
        exit /b 1
    )
)

:: Set environment paths
set "PATH=%~dp0ffmpeg;%PATH%"

:: Run auto setup & sync in background if needed
"%PYTHON_EXE%" setup_environment.py

echo.
echo [1/2] Starting AI Studio & Sound Designer Service (Port 5682)...
start /b "OpenCut AI Studio" "%PYTHON_EXE%" "%~dp0server\sound_designer_service.py"

echo [2/2] Starting OpenCut Core Server (Port 5679)...
if exist "%~dp0server\OpenCut-Server.exe" (
    "%~dp0server\OpenCut-Server.exe"
) else (
    echo [INFO] Running Python Core Server fallback...
    "%PYTHON_EXE%" "%~dp0server\pipeline.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server closed. Press any key to exit.
    pause
)
