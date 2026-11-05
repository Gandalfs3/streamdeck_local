# Stream Deck Local & Remote 🎛️

Un Stream Deck táctil, ligero y personalizable que convierte cualquier tablet vieja (Android 4.0.3+), celular o navegador web en una consola de atajos para tu PC con Windows.

![Stream Deck](https://img.shields.io/badge/Windows-Supported-blue?logo=windows)
![Python](https://img.shields.io/badge/Python-3.x-yellow?logo=python)
![Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare-orange?logo=cloudflare)

---

## 🚀 Características

- **🎵 Control Multimedia por Hardware:** Control directo del volumen maestro de Windows, mute, play/pausa y cambio de pista usando la API nativa de audio (`IAudioEndpointVolume` via Core Audio).
- **💻 Atajos de Desarrollo:** Botones dedicados para abrir VS Code, Windows Terminal (PowerShell), Localhost en navegador y Calculadora.
- **🖥️ Control de Sistema:** Conmutador para mostrar escritorio (`ToggleDesktop`) y botón para bloquear PC (`LockWorkStation`).
- **📊 Telemetría en Vivo:** Widget superior con monitoreo en tiempo real del uso de **CPU (%)** y **Memoria RAM (%)**.
- **🌐 Acceso Local y Remoto:** Funciona en la misma red Wi-Fi y genera un túnel seguro con **Cloudflare Tunnel** para acceder desde cualquier lugar o sortear firewalls locales.
- **📱 Compatibilidad Retro:** Interfaz diseñada en HTML5/CSS y Vanilla ES5 con iconos vectoriales SVG limpios. Funciona tanto en dispositivos modernos como en navegadores antiguos (ej. Android 4.0 Ice Cream Sandwich).

---

## 📂 Estructura del Proyecto

```text
stream-deck/
├── server.py              # Servidor HTTP nativo en Python (API y telemetría)
├── index.html             # Interfaz web táctil con iconos SVG y CSS responsivo
├── audio_tool.cs          # Módulo nativo en C# para interactuar con Windows Core Audio
├── audio_tool.exe         # Binario compilado ligero para control de hardware
├── iniciar_streamdeck.bat # Script de inicio rápido en 1 clic (Servidor + Túnel)
└── README.md
```

---

## 🛠️ Cómo Iniciar

1. Haz doble clic en **`iniciar_streamdeck.bat`** (o ejecuta `python server.py`).
2. Se iniciará el servidor local en el puerto `5000` y levantará un túnel temporal de Cloudflare.
3. Abre en tu tablet o celular:
   - **En red local:** `http://<IP-DE-TU-PC>:5000`
   - **Por Cloudflare Tunnel:** El enlace `https://xxxx.trycloudflare.com` generado en la consola.
