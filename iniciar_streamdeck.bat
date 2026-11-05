@echo off
title Stream Deck Launcher
cd /d "%~dp0"

if exist StreamDeck.exe (
    start "" StreamDeck.exe
    exit
) else (
    start "" python app.py
    exit
)
