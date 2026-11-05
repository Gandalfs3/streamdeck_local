# Stream Deck Local & Remote 🎛️

Un Stream Deck táctil, ligero y personalizable que convierte cualquier tablet vieja (Android 4.0.3+), celular o navegador web en una consola de atajos para tu PC con Windows.

[![Descargar StreamDeck.exe](https://img.shields.io/badge/Descargar-StreamDeck.exe-brightgreen?style=for-the-badge&logo=windows)](https://github.com/Gandalfs3/streamdeck_local/releases/latest/download/StreamDeck.exe)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue?logo=windows)
![Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare-orange?logo=cloudflare)

---

## ⚡ Descarga Rápida (Sin instalar nada)

Para usarlo en cualquier PC con Windows sin tener que descargar el código ni instalar Python:

1. Ve a la sección de **[Releases](https://github.com/Gandalfs3/streamdeck_local/releases/latest)**.
2. Descarga **`StreamDeck.exe`**.
3. Haz doble clic en el archivo: se abrirá una ventana elegante con tu enlace de conexión y un botón para copiarlo o abrirlo.
4. Abre ese enlace en tu tablet o celular y ¡listo!

---

## 🚀 Características

- **🎵 Control Multimedia por Hardware:** Control directo del volumen maestro de Windows, mute, play/pausa y cambio de pista usando la API nativa de audio (`IAudioEndpointVolume` via Core Audio).
- **💻 Atajos de Desarrollo:** Botones dedicados para abrir VS Code, Windows Terminal (PowerShell), Localhost en navegador y Calculadora.
- **🖥️ Control de Sistema:** Conmutador para mostrar escritorio (`ToggleDesktop`) y botón para bloquear PC (`LockWorkStation`).
- **📊 Telemetría en Vivo:** Widget superior con monitoreo en tiempo real del uso de **CPU (%)** y **Memoria RAM (%)**.
- **🌐 Acceso Remoto Automático:** Genera un túnel seguro con **Cloudflare Tunnel** para acceder desde cualquier lugar o sortear firewalls locales sin configurar puertos.
- **📱 Compatibilidad Retro Extrema:** Interfaz diseñada en HTML5/CSS y Vanilla ES5 con iconos vectoriales SVG limpios. Funciona tanto en dispositivos modernos como en navegadores antiguos (ej. Android 4.0 Ice Cream Sandwich).

---

## 📂 Estructura del Código

```text
stream-deck/
├── app.py                 # Aplicación con GUI (Tkinter), servidor HTTP y gestor de Cloudflare Tunnel
├── index.html             # Interfaz web táctil con iconos SVG y CSS retrocompatible
├── audio_tool.cs          # Módulo nativo en C# para interactuar con Windows Core Audio
├── audio_tool.exe         # Binario compilado para control directo de hardware
└── README.md
```
