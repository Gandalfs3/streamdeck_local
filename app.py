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
from PIL import Image, ImageTk
import qrcode

PORT = 5000

# Directorio base (compatible con PyInstaller y ejecucion normal)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
    # Si el usuario tiene un index.html personalizado en su carpeta, usarlo prioritariamente
    if os.path.exists(os.path.join(APP_DIR, "index.html")):
        INDEX_HTML_PATH = os.path.join(APP_DIR, "index.html")
    else:
        INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

    if os.path.exists(os.path.join(APP_DIR, "audio_tool.exe")):
        AUDIO_TOOL_PATH = os.path.join(APP_DIR, "audio_tool.exe")
    else:
        AUDIO_TOOL_PATH = os.path.join(BASE_DIR, "audio_tool.exe")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR
    INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")
    AUDIO_TOOL_PATH = os.path.join(BASE_DIR, "audio_tool.exe")

CLOUDFLARED_PATH = os.path.join(APP_DIR, "cloudflared.exe")

# --- Telemetria Nativa de Windows (Sin psutil) ---
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
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
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
            # Cache busting estricto para evitar que el navegador guarde versiones viejas
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
        # Silenciar logs en consola
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

# --- Aplicacion de Interfaz Grafica (GUI) Moderna ---
class StreamDeckApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stream Deck PC Server")
        self.root.geometry("740x510")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d1117")

        self.cloudflared_proc = None
        self.public_url = ""
        self.local_ip = get_local_ip()
        self.local_url = f"http://{self.local_ip}:{PORT}"
        self.current_qr_target = "public"
        self.qr_photo = None

        self.build_ui()
        self.start_server()
        self.start_tunnel_thread()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def generate_qr(self, text, size=180):
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=4,
                border=2,
            )
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#000000", back_color="#ffffff").convert("RGB")
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def update_qr_display(self):
        target_url = self.public_url if self.current_qr_target == "public" and self.public_url else self.local_url
        if target_url:
            self.qr_photo = self.generate_qr(target_url, size=180)
            if self.qr_photo:
                self.qr_label.config(image=self.qr_photo, text="")
            else:
                self.qr_label.config(text="QR no disponible")

    def switch_qr(self, target):
        self.current_qr_target = target
        if target == "public":
            self.btn_qr_pub.config(bg="#1f6feb", fg="#ffffff")
            self.btn_qr_loc.config(bg="#21262d", fg="#8b949e")
        else:
            self.btn_qr_loc.config(bg="#1f6feb", fg="#ffffff")
            self.btn_qr_pub.config(bg="#21262d", fg="#8b949e")
        self.update_qr_display()

    def build_ui(self):
        # 1. BARRA SUPERIOR / HEADER
        header_frame = tk.Frame(self.root, bg="#161b22", padx=24, pady=14, highlightbackground="#30363d", highlightthickness=1)
        header_frame.pack(fill="x")

        title_left = tk.Frame(header_frame, bg="#161b22")
        title_left.pack(side="left")

        title_lbl = tk.Label(title_left, text="🎛️ Stream Deck PC", font=("Segoe UI", 16, "bold"), fg="#58a6ff", bg="#161b22")
        title_lbl.pack(side="left")

        badge_lbl = tk.Label(title_left, text="v1.0.1 PRO", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#238636", padx=6, pady=1)
        badge_lbl.pack(side="left", padx=10)

        self.status_lbl = tk.Label(header_frame, text="● Conectando túnel seguro...", font=("Segoe UI", 11, "bold"), fg="#d29922", bg="#161b22")
        self.status_lbl.pack(side="right")

        # 2. CUERPO PRINCIPAL (2 COLUMNAS)
        body_frame = tk.Frame(self.root, bg="#0d1117", padx=20, pady=16)
        body_frame.pack(fill="both", expand=True)

        # --- COLUMNA IZQUIERDA: TARJETA QR (260px) ---
        qr_card = tk.Frame(body_frame, bg="#161b22", width=250, padx=14, pady=14, highlightbackground="#30363d", highlightthickness=1)
        qr_card.pack(side="left", fill="y", padx=(0, 16))
        qr_card.pack_propagate(False)

        qr_title = tk.Label(qr_card, text="📱 Escanear con Cámara", font=("Segoe UI", 11, "bold"), fg="#f0f6fc", bg="#161b22")
        qr_title.pack(anchor="center", pady=(0, 10))

        # Contenedor del QR
        self.qr_frame_box = tk.Frame(qr_card, bg="#ffffff", bd=3, relief="solid")
        self.qr_frame_box.pack(anchor="center", pady=(0, 10))

        self.qr_label = tk.Label(self.qr_frame_box, bg="#ffffff", width=180, height=180, text="Generando QR...", font=("Segoe UI", 9), fg="#666666")
        self.qr_label.pack()

        # Selector de QR
        qr_btn_frame = tk.Frame(qr_card, bg="#161b22")
        qr_btn_frame.pack(fill="x", pady=(0, 8))

        self.btn_qr_pub = tk.Button(qr_btn_frame, text="☁️ Remoto", font=("Segoe UI", 9, "bold"), bg="#1f6feb", fg="#ffffff", bd=0, padx=6, pady=4, cursor="hand2", command=lambda: self.switch_qr("public"))
        self.btn_qr_pub.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_qr_loc = tk.Button(qr_btn_frame, text="📶 Wi-Fi", font=("Segoe UI", 9), bg="#21262d", fg="#8b949e", bd=0, padx=6, pady=4, cursor="hand2", command=lambda: self.switch_qr("local"))
        self.btn_qr_loc.pack(side="right", expand=True, fill="x", padx=(4, 0))

        qr_desc = tk.Label(qr_card, text="Apunta la cámara de tu tablet o móvil para abrir al instante.", font=("Segoe UI", 8), fg="#8b949e", bg="#161b22", wraplength=210, justify="center")
        qr_desc.pack(anchor="center")

        # --- COLUMNA DERECHA: TARJETAS DE CONEXION ---
        conn_frame = tk.Frame(body_frame, bg="#0d1117")
        conn_frame.pack(side="right", fill="both", expand=True)

        # TARJETA 1: ENLACE PÚBLICO REMOTO (CLOUDFLARE)
        card1 = tk.Frame(conn_frame, bg="#161b22", padx=16, pady=14, highlightbackground="#30363d", highlightthickness=1)
        card1.pack(fill="x", pady=(0, 14))

        card1_top = tk.Frame(card1, bg="#161b22")
        card1_top.pack(fill="x", pady=(0, 4))

        lbl_c1_title = tk.Label(card1_top, text="☁️ Enlace Remoto / Internet", font=("Segoe UI", 12, "bold"), fg="#58a6ff", bg="#161b22")
        lbl_c1_title.pack(side="left")

        lbl_c1_rec = tk.Label(card1_top, text="RECOMENDADO", font=("Segoe UI", 8, "bold"), fg="#3fb950", bg="#161b22")
        lbl_c1_rec.pack(side="right")

        lbl_c1_desc = tk.Label(card1, text="Funciona desde cualquier red o dispositivo sin configurar el router:", font=("Segoe UI", 9), fg="#8b949e", bg="#161b22")
        lbl_c1_desc.pack(anchor="w", pady=(0, 8))

        # URL Entry Remoto
        url_box1 = tk.Frame(card1, bg="#21262d", padx=8, pady=6, highlightbackground="#30363d", highlightthickness=1)
        url_box1.pack(fill="x", pady=(0, 10))

        self.url_pub_var = tk.StringVar(value="Generando enlace seguro...")
        self.entry_pub = tk.Entry(url_box1, textvariable=self.url_pub_var, font=("Consolas", 11, "bold"), fg="#3fb950", bg="#21262d", bd=0, readonlybackground="#21262d", state="readonly")
        self.entry_pub.pack(fill="x")

        # Botones Remoto
        b1_frame = tk.Frame(card1, bg="#161b22")
        b1_frame.pack(fill="x")

        self.btn_copy_pub = tk.Button(b1_frame, text="📋 Copiar Enlace", font=("Segoe UI", 9, "bold"), bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.copy_pub_url)
        self.btn_copy_pub.pack(side="left", padx=(0, 8))

        self.btn_open_pub = tk.Button(b1_frame, text="🌐 Abrir en esta PC", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.open_pub_browser)
        self.btn_open_pub.pack(side="left")

        # TARJETA 2: RED LOCAL WI-FI
        card2 = tk.Frame(conn_frame, bg="#161b22", padx=16, pady=14, highlightbackground="#30363d", highlightthickness=1)
        card2.pack(fill="x")

        card2_top = tk.Frame(card2, bg="#161b22")
        card2_top.pack(fill="x", pady=(0, 4))

        lbl_c2_title = tk.Label(card2_top, text="📶 Conexión Red Local (Wi-Fi)", font=("Segoe UI", 12, "bold"), fg="#7ee787", bg="#161b22")
        lbl_c2_title.pack(side="left")

        lbl_c2_desc = tk.Label(card2, text="Si tu tablet y la PC están conectadas a la misma red Wi-Fi:", font=("Segoe UI", 9), fg="#8b949e", bg="#161b22")
        lbl_c2_desc.pack(anchor="w", pady=(0, 8))

        # URL Entry Local
        url_box2 = tk.Frame(card2, bg="#21262d", padx=8, pady=6, highlightbackground="#30363d", highlightthickness=1)
        url_box2.pack(fill="x", pady=(0, 10))

        self.url_loc_var = tk.StringVar(value=self.local_url)
        self.entry_loc = tk.Entry(url_box2, textvariable=self.url_loc_var, font=("Consolas", 11, "bold"), fg="#58a6ff", bg="#21262d", bd=0, readonlybackground="#21262d", state="readonly")
        self.entry_loc.pack(fill="x")

        # Botones Local
        b2_frame = tk.Frame(card2, bg="#161b22")
        b2_frame.pack(fill="x")

        self.btn_copy_loc = tk.Button(b2_frame, text="📋 Copiar IP Local", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.copy_loc_url)
        self.btn_copy_loc.pack(side="left", padx=(0, 8))

        self.btn_open_loc = tk.Button(b2_frame, text="🌐 Probar Localmente", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.open_loc_browser)
        self.btn_open_loc.pack(side="left")

        # 3. PIE DE PAGINA
        footer_frame = tk.Frame(self.root, bg="#0d1117", padx=24, pady=8)
        footer_frame.pack(fill="x", side="bottom")

        lbl_footer = tk.Label(footer_frame, text="💡 Stream Deck Local • Código Abierto • Puerto 5000", font=("Segoe UI", 8), fg="#484f58", bg="#0d1117")
        lbl_footer.pack(side="left")

        lbl_hint = tk.Label(footer_frame, text="Usa F11 en la web para Pantalla Completa", font=("Segoe UI", 8), fg="#58a6ff", bg="#0d1117")
        lbl_hint.pack(side="right")

    def copy_pub_url(self):
        url = self.url_pub_var.get()
        if "http" in url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.btn_copy_pub.config(text="✅ ¡Copiado!", bg="#1f6feb")
            self.root.after(2000, lambda: self.btn_copy_pub.config(text="📋 Copiar Enlace", bg="#238636"))

    def copy_loc_url(self):
        url = self.url_loc_var.get()
        if "http" in url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.btn_copy_loc.config(text="✅ ¡Copiado!", bg="#1f6feb")
            self.root.after(2000, lambda: self.btn_copy_loc.config(text="📋 Copiar IP Local", bg="#21262d"))

    def open_pub_browser(self):
        url = self.url_pub_var.get()
        if "http" in url:
            subprocess.Popen(f'start "" "{url}"', shell=True)

    def open_loc_browser(self):
        url = self.url_loc_var.get()
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
        # Actualizar QR local inmediatamente de respaldo
        self.root.after(0, self.update_qr_display)

        if not os.path.exists(CLOUDFLARED_PATH):
            self.url_pub_var.set("Descargando túnel de conexión...")
            try:
                cf_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
                urllib.request.urlretrieve(cf_url, CLOUDFLARED_PATH)
            except Exception as e:
                self.url_pub_var.set(f"Error descargando túnel: {e}")
                return

        time.sleep(1)

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

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
            self.url_pub_var.set(f"Error iniciando túnel: {e}")

    def update_url_found(self, url):
        self.url_pub_var.set(url)
        self.status_lbl.config(text="● En Línea", fg="#3fb950")
        self.update_qr_display()

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
