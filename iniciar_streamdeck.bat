@echo off
title Stream Deck Launcher
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% equ 0 (
    if exist app.py (
        start "" python app.py
        exit
    )
)

if exist StreamDeck.exe (
    start "" StreamDeck.exe
    exit
) else (
    start "" python app.py
    exit
)
