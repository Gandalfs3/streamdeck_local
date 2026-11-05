# Stream Deck Local & Remote 🎛️

Un Stream Deck táctil, ligero y personalizable que convierte cualquier tablet vieja (Android 4.0.3+), smartphone o navegador web en una consola de atajos para tu PC con Windows.

[![Descargar StreamDeck.exe](https://img.shields.io/badge/Descargar-StreamDeck.exe-brightgreen?style=for-the-badge&logo=windows)](https://github.com/Gandalfs3/streamdeck_local/releases/latest/download/StreamDeck.exe)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue?logo=windows)
![Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare-orange?logo=cloudflare)
![Open Source](https://img.shields.io/badge/License-MIT-purple)

---

## ⚡ Descarga Rápida (Sin instalar Python ni configurar nada)

1. Ve a la sección de **[Releases](https://github.com/Gandalfs3/streamdeck_local/releases/latest)**.
2. Descarga **`StreamDeck.exe`**.
3. Haz doble clic en el archivo: se abrirá una consola visual en tu PC con un **Código QR** y los enlaces de conexión.
4. **Escanea el código QR** con la cámara de tu tablet o celular para abrir tu Stream Deck de inmediato.

---

## 🚀 Características Principales

- **📱 Código QR Integrado:** Escaneo instantáneo desde cualquier dispositivo móvil sin tener que escribir URLs manualmente.
- **✨ Diseño Táctil 3D:** Teclas estilo consola física con reflejo gloss, animación de pulsación, vibración háptica y sonido de click mecánico opcional sintetizado por hardware.
- **🎵 Control Multimedia por Hardware:** Control directo del volumen maestro de Windows, mute, play/pausa y cambio de pista usando la API nativa de audio de Windows (`IAudioEndpointVolume` via Core Audio).
- **💻 Atajos de Desarrollo y Sistema:** Botones dedicados para abrir VS Code, Windows Terminal (PowerShell), Localhost en navegador, Calculadora, Mostrar Escritorio y Bloqueo de PC.
- **📊 Telemetría en Vivo:** Widget superior con monitoreo en tiempo real del uso de **CPU (%)** y **Memoria RAM (%)** con barras de color dinámicas.
- **🌐 Acceso Remoto Automático:** Integra **Cloudflare Tunnel** para acceder desde cualquier lugar o red Wi-Fi sin abrir puertos ni configurar tu router.
- **📶 Modo Red Local (Wi-Fi):** Enlace directo de ultra baja latencia (`http://<IP-LOCAL>:5000`) para usar dentro de la misma red doméstica.
- **📱 Máxima Compatibilidad Retro:** Interfaz desarrollada en HTML5/CSS y Vanilla ES5 con gráficos vectoriales SVG. Funciona en smartphones modernos y en tablets antiguas (ej. Android 4.0 Ice Cream Sandwich).
- **⛶ Modo Pantalla Completa:** Botón integrado para ocultar barras del navegador y transformar la tablet en una superficie de control dedicada.

---

## 📂 Estructura del Proyecto

```text
streamdeck_local/
├── StreamDeck.exe         # Ejecutable portátil standalone para Windows
├── app.py                 # Servidor HTTP, interfaz de escritorio Tkinter con QR y túnel Cloudflare
├── index.html             # Interfaz web táctil con iconos SVG y CSS retrocompatible
├── audio_tool.cs          # Módulo nativo en C# para interactuar con Windows Core Audio
├── audio_tool.exe         # Binario de hardware compiled con winexe (sin ventanas parpadeantes)
├── iniciar_streamdeck.bat # Lanzador rápido
└── README.md
```

---

## 🛠️ Desarrollo y Personalización

Si deseas modificar los botones o acciones:
1. Clona el repositorio:
   ```bash
   git clone https://github.com/Gandalfs3/streamdeck_local.git
   cd streamdeck_local
   ```
2. Instala las dependencias:
   ```bash
   pip install qrcode pillow pyinstaller
   ```
3. Ejecuta en modo desarrollo:
   ```bash
   python app.py
   ```
4. Para compilar tu propio `.exe`:
   ```bash
   pyinstaller --noconfirm StreamDeck.spec
   ```
