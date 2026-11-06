# Stream Deck Local & Remote 🎛️

Un **Stream Deck táctil, ligero y de código abierto** que transforma cualquier tablet vieja (Android 4.0.3+), smartphone o navegador web en una consola física de atajos para tu PC con Windows.

[![Descargar StreamDeck.exe](https://img.shields.io/badge/Descargar-StreamDeck.exe-brightgreen?style=for-the-badge&logo=windows)](https://github.com/Gandalfs3/streamdeck_local/releases/latest/download/StreamDeck.exe)
[![Autor](https://img.shields.io/badge/Creado%20por-Gandalfs3-blue?style=for-the-badge&logo=github)](https://github.com/Gandalfs3)
![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue?logo=windows)
![Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare-orange?logo=cloudflare)
![Licencia](https://img.shields.io/badge/License-MIT-purple)

---

## ⚡ Guía Rápida para Usuarios (Sin instalar nada)

No necesitas tener conocimientos técnicos ni instalar Python para utilizarlo:

1. Ve a la sección de **[Releases de GitHub](https://github.com/Gandalfs3/streamdeck_local/releases/latest)**.
2. Descarga el ejecutable **`StreamDeck.exe`**.
3. Haz doble clic en **`StreamDeck.exe`** en tu PC con Windows. Se abrirá una ventana con un **Código QR** y los enlaces de conexión.
4. **Escanea el código QR con la cámara de tu tablet o celular** (o abre el enlace en su navegador) y ¡listo! Ya puedes controlar tu PC con un toque.

---

## 🌐 Modos de Conexión Disponibles

El programa incluye dos formas inteligentes de conectarse:

### 1. 📶 Red Local Wi-Fi (Opción recomendada en casa)
* **¿Cuándo usarlo?:** Si tu tablet/celular y tu PC están conectados al mismo módem o red Wi-Fi.
* **Ventajas:** 
  * **Cero lag:** Latencia de menos de 1 ms, respuesta inmediata al pulsar cualquier tecla.
  * **100% privado y sin internet:** No consume datos ni depende de servidores externos.
  * **Enlace fijo:** Dirección del estilo `http://192.168.1.X:5000` que nunca cambia.
  * Viene activado por defecto en el código QR.

### 2. ☁️ Túnel Remoto Cloudflare (Para usar fuera de casa)
* **¿Cuándo usarlo?:** Si quieres controlar tu PC desde datos móviles (4G/5G) o desde otra red Wi-Fi distinta.
* **Ventajas:**
  * No necesitas abrir puertos en tu router ni saber sobre DNS dinámico.
  * Crea una conexión segura HTTPS (`.trycloudflare.com`) automáticamente.
  * *Nota: La primera vez que se genera un túnel, Cloudflare puede tardar de 20 a 30 segundos en propagar el dominio por internet.*

---

## 🚀 Características y Atajos Incluidos

* **⚙️ Personalización Total de Botones (v1.1.0):** Modo de edición interactivo con el botón `⚙️ Personalizar`. Crea, modifica el nombre, icono, color y acción de cualquier botón o bórralo con un toque.
* **🚀 Lanzador de Aplicaciones y Programas de PC:** Escaneo automático de programas instalados en tu menú de inicio (Chrome, Edge, Spotify, Discord, VS Code, Postman, etc.) con resolución nativa de accesos directos `.lnk` y apertura directa en tu monitor.
* **🔊 Soundboard / Efectos de Sonido:** Botones para disparar efectos de sonido en vivo en tu PC con soporte para elegir archivos locales o subir tus propios audios `.mp3` o `.wav` directamente desde el móvil o tablet.
* **🌐 Enlaces Web Directos:** Crea accesos rápidos para abrir cualquier URL o servicio web con un toque (YouTube, Twitch, ChatGPT, GitHub, etc.).
* **📱 Código QR Interactivo:** Conexión en 2 segundos apuntando la cámara del móvil.
* **✨ Botones Táctiles 3D:** Diseño inspirado en consolas Elgato con brillo gloss, animación física de pulsación y retroalimentación háptica.
* **🔉 Sonido Mecánico Táctil Opcional:** Sonido de click mecánico sintetizado por hardware (*Web Audio API*), 100% offline y conmutable con el botón `🔊 Sonido`.
* **🎵 Control Multimedia Directo:** Conexión nativa a la API de Windows Audio (`IAudioEndpointVolume` via Core Audio COM) para subir/bajar volumen maestro sin depender de atajos de teclado simulados.
* **💻 Atajos Productivos por Defecto:** Botones para VS Code, Terminal PowerShell, Calculadora, Minimizar al Escritorio y Bloqueo de PC.
* **📊 Telemetría en Tiempo Real:** Monitor superior con porcentaje de uso de **CPU** y memoria **RAM** con barras dinámicas de advertencia.
* **⛶ Modo Pantalla Completa:** Oculta barras de navegación para usar tablets como consolas dedicadas fijas.
* **📱 Compatibilidad Retro Extrema:** Desarrollado en Vanilla ES5 y gráficos vectoriales SVG compatibles tanto con smartphones modernos como con tablets antiguas (ej. Android 4.0 Ice Cream Sandwich).

---

## 💡 Consejos para Reutilizar Tablets Viejas

Si tienes una tablet antigua en un cajón y quieres dejarla fija como panel de control en tu escritorio:
1. Conéctala a tu cargador y a tu Wi-Fi.
2. Abre la URL local en el navegador de la tablet.
3. Toca el botón **`⛶ Pantalla Completa`** en la barra superior.
4. En el menú de tu navegador, selecciona *"Añadir a la pantalla de inicio"* para abrirlo como si fuera una aplicación nativa sin barras.

---

## 🛠️ Personalización y Desarrollo (Para Programadores)

Si deseas modificar los atajos, cambiar colores o compilar tu propia versión:

### 1. Clonar el repositorio
```bash
git clone https://github.com/Gandalfs3/streamdeck_local.git
cd streamdeck_local
```

### 2. Instalar dependencias
```bash
pip install qrcode pillow pyinstaller
```

### 3. Ejecutar en desarrollo
```bash
python app.py
```

### 4. Estructura del código
* `app.py`: Servidor HTTP multihilo, interfaz gráfica Tkinter con generador QR offline y gestor de túnel Cloudflare.
* `index.html`: Consola web interactiva con botones 3D, iconos SVG y diseño responsivo.
* `audio_tool.cs`: Módulo nativo en C# que interactúa con la API Core Audio de Windows.
* `audio_tool.exe`: Binario compilado con `/target:winexe` para evitar ventanas de consola parpadeantes.
* `StreamDeck.spec`: Archivo de configuración para PyInstaller.

### 5. Compilar tu propio `.exe`
```bash
pyinstaller --noconfirm StreamDeck.spec
```

---

## 👤 Autor & Créditos

Este proyecto fue ideado, creado y desarrollado por **[Gandalfs3](https://github.com/Gandalfs3)** como una herramienta de código abierto y gratuita para la comunidad.

* **GitHub:** [@Gandalfs3](https://github.com/Gandalfs3)
* **Repositorio Oficial:** [https://github.com/Gandalfs3/streamdeck_local](https://github.com/Gandalfs3/streamdeck_local)
* **Licencia:** MIT (Permite uso personal, comercial, modificación y distribución libre).
