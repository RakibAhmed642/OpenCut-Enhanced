@echo off
setlocal enabledelayedexpansion
title OpenCut Enhanced Setup
cd /d "%~dp0"

echo ===================================================
echo     OpenCut Enhanced - 1-Click Fast Setup
echo ===================================================

set "PY=python"
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "C:\Python313\python.exe" (
        set "PY=C:\Python313\python.exe"
    ) else if exist "C:\Python312\python.exe" (
        set "PY=C:\Python312\python.exe"
    ) else if exist "C:\Python311\python.exe" (
        set "PY=C:\Python311\python.exe"
    ) else (
        echo [!] Python 3.10+ not found in PATH or standard folders.
        pause
        exit /b 1
    )
)

"%PY%" setup_environment.py

echo.
echo Press any key to finish...
pause >nul
