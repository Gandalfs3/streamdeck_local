import os
import sys
import time
import json
import re
import socket
import threading
import subprocess
import urllib.request
import ctypes
from ctypes import wintypes
import http.server
import tkinter as tk
from tkinter import messagebox

PORT = 5000

# Directorio base (compatible con PyInstaller y ejecucion normal)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR

INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")
if not os.path.exists(INDEX_HTML_PATH):
    INDEX_HTML_PATH = os.path.join(APP_DIR, "index.html")

AUDIO_TOOL_PATH = os.path.join(BASE_DIR, "audio_tool.exe")
if not os.path.exists(AUDIO_TOOL_PATH):
    AUDIO_TOOL_PATH = os.path.join(APP_DIR, "audio_tool.exe")

CLOUDFLARED_PATH = os.path.join(APP_DIR, "cloudflared.exe")

# --- Telemetria ---
class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)
    ]

prev_idle = 0
prev_kernel = 0
prev_user = 0

def get_stats():
    global prev_idle, prev_kernel, prev_user
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    ram_load = stat.dwMemoryLoad
    total_gb = round(stat.ullTotalPhys / (1024**3), 1)
    used_gb = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024**3), 1)

    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
    i = (idle.dwHighDateTime << 32) | idle.dwLowDateTime
    k = (kernel.dwHighDateTime << 32) | kernel.dwLowDateTime
    u = (user.dwHighDateTime << 32) | user.dwLowDateTime

    idle_diff = i - prev_idle
    kernel_diff = k - prev_kernel
    user_diff = u - prev_user
    total = kernel_diff + user_diff

    prev_idle, prev_kernel, prev_user = i, k, u
    cpu_load = 0
    if total > 0 and prev_idle != i:
        cpu_load = max(0, min(100, int(100.0 * (1.0 - (idle_diff / total)))))

    return {
        "cpu": cpu_load,
        "ram": ram_load,
        "ram_used": used_gb,
        "ram_total": total_gb
    }

CREATE_NO_WINDOW = 0x08000000

def run_audio_tool(cmd):
    if os.path.exists(AUDIO_TOOL_PATH):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            subprocess.Popen([AUDIO_TOOL_PATH, cmd], startupinfo=startupinfo, creationflags=CREATE_NO_WINDOW)
        except Exception:
            pass

def execute_action(action):
    if action == "vol_up":
        run_audio_tool("up")
    elif action == "vol_down":
        run_audio_tool("down")
    elif action == "vol_mute":
        run_audio_tool("mute")
    elif action == "desktop":
        run_audio_tool("desktop")
    elif action == "play_pause":
        run_audio_tool("play_pause")
    elif action == "next_track":
        run_audio_tool("next")
    elif action == "prev_track":
        run_audio_tool("prev")
    elif action == "open_code":
        code_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe")
        if os.path.exists(code_path):
            os.startfile(code_path)
        else:
            subprocess.Popen("start code", shell=True, creationflags=CREATE_NO_WINDOW)
    elif action == "open_terminal":
        subprocess.Popen("start powershell", shell=True, creationflags=CREATE_NO_WINDOW)
    elif action == "open_browser":
        os.startfile("http://localhost:3000")
    elif action == "open_calc":
        subprocess.Popen("calc", creationflags=CREATE_NO_WINDOW)
    elif action == "lock_pc":
        ctypes.windll.user32.LockWorkStation()

class StreamDeckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(get_stats()).encode("utf-8"))
            return

        if self.path == "/" or self.path == "/index.html":
            if os.path.exists(INDEX_HTML_PATH):
                with open(INDEX_HTML_PATH, "rb") as f:
                    content = f.read()
            else:
                content = b"<h1>Stream Deck UI file not found</h1>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/action":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                execute_action(payload.get("action"))
                res = {"status": "ok"}
            except Exception as e:
                res = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Silenciar logs ruidosos en consola
        return

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# --- Aplicacion de Interfaz Grafica (GUI) ---
class StreamDeckApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Deck PC")
        self.root.geometry("520x330")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d1117")

        self.cloudflared_proc = None
        self.public_url = "Iniciando conexion..."
        self.local_ip = get_local_ip()

        self.build_ui()
        self.start_server()
        self.start_tunnel_thread()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        # Titulo y Estado
        header_frame = tk.Frame(self.root, bg="#161b22", padx=20, pady=12)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(header_frame, text="🎛️ Stream Deck Server", font=("Segoe UI", 16, "bold"), fg="#58a6ff", bg="#161b22")
        title_lbl.pack(side="left")

        self.status_lbl = tk.Label(header_frame, text="● Conectando...", font=("Segoe UI", 11, "bold"), fg="#e3b341", bg="#161b22")
        self.status_lbl.pack(side="right")

        # Contenido Principal
        content_frame = tk.Frame(self.root, bg="#0d1117", padx=25, pady=20)
        content_frame.pack(fill="both", expand=True)

        lbl1 = tk.Label(content_frame, text="Enlace para tu Tablet, Celular u otro dispositivo:", font=("Segoe UI", 11), fg="#c9d1d9", bg="#0d1117")
        lbl1.pack(anchor="w", pady=(0, 6))

        # Campo con la URL
        url_frame = tk.Frame(content_frame, bg="#21262d", padx=8, pady=6, highlightbackground="#30363d", highlightthickness=1)
        url_frame.pack(fill="x", pady=(0, 15))

        self.url_var = tk.StringVar(value="Generando enlace seguro...")
        self.url_entry = tk.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 12, "bold"), fg="#3fb950", bg="#21262d", bd=0, readonlybackground="#21262d", state="readonly")
        self.url_entry.pack(fill="x")

        # Botones de Accion
        btn_frame = tk.Frame(content_frame, bg="#0d1117")
        btn_frame.pack(fill="x", pady=(0, 15))

        self.copy_btn = tk.Button(btn_frame, text="📋 Copiar Enlace", font=("Segoe UI", 10, "bold"), bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff", bd=0, padx=14, pady=8, cursor="hand2", command=self.copy_url)
        self.copy_btn.pack(side="left", padx=(0, 10))

        self.open_btn = tk.Button(btn_frame, text="🌐 Abrir en esta PC", font=("Segoe UI", 10), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=14, pady=8, cursor="hand2", command=self.open_in_browser)
        self.open_btn.pack(side="left")

        # IP Local alternativa
        local_info = f"Red local (mismo Wi-Fi): http://{self.local_ip}:{PORT}"
        lbl_local = tk.Label(content_frame, text=local_info, font=("Segoe UI", 9), fg="#8b949e", bg="#0d1117")
        lbl_local.pack(anchor="w")

    def copy_url(self):
        url = self.url_var.get()
        if "http" in url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.copy_btn.config(text="✅ ¡Copiado!", bg="#1f6feb")
            self.root.after(2000, lambda: self.copy_btn.config(text="📋 Copiar Enlace", bg="#238636"))

    def open_in_browser(self):
        url = self.url_var.get()
        if "http" in url:
            subprocess.Popen(f'start "" "{url}"', shell=True)

    def start_server(self):
        try:
            self.httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), StreamDeckHandler)
            t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            t.start()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el servidor en puerto {PORT}:\n{e}")

    def start_tunnel_thread(self):
        t = threading.Thread(target=self.run_cloudflared, daemon=True)
        t.start()

    def run_cloudflared(self):
        # Descarga automatica de cloudflared si no existe
        if not os.path.exists(CLOUDFLARED_PATH):
            self.url_var.set("Descargando túnel de conexión...")
            try:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
                urllib.request.urlretrieve(cf_url, CLOUDFLARED_PATH)
            except Exception as e:
                self.url_var.set(f"Error descargando túnel: {e}")
                return

        # Esperar 1 segundo a que el servidor HTTP local este listo
        time.sleep(1)

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # Oculta ventana negra de consola

            self.cloudflared_proc = subprocess.Popen(
                [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            for line in iter(self.cloudflared_proc.stdout.readline, ''):
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    found_url = match.group(0)
                    self.public_url = found_url
                    self.root.after(0, self.update_url_found, found_url)
                    break
        except Exception as e:
            self.url_var.set(f"Error iniciando túnel: {e}")

    def update_url_found(self, url):
        self.url_var.set(url)
        self.status_lbl.config(text="● En Línea", fg="#3fb950")

    def on_close(self):
        if self.cloudflared_proc:
            try:
                self.cloudflared_proc.terminate()
            except Exception:
                pass
        self.root.destroy()
        os._exit(0)

if __name__ == "__main__":
    get_stats()
    root = tk.Tk()
    app = StreamDeckApp(root)
    root.mainloop()
