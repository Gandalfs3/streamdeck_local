@echo off
title Stream Deck Server PC
cd /d "%~dp0"
echo ====================================================
echo  Iniciando Stream Deck Server...
echo ====================================================
start "StreamDeck-Python" python server.py
timeout /t 2 /nobreak >nul

if not exist cloudflared.exe (
    echo Descargando cloudflared portable para acceso remoto...
    curl.exe -s -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -o cloudflared.exe
)

if exist cloudflared.exe (
    echo.
    echo Conectando Cloudflare Tunnel...
    echo (Mira el enlace https://xxxx.trycloudflare.com que aparecera abajo)
    echo ====================================================
    cloudflared.exe tunnel --url http://localhost:5000
) else (
    echo Servidor activo localmente en http://localhost:5000
    pause
)
