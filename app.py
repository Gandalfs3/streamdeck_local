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
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
SOUNDS_DIR = os.path.join(APP_DIR, "sounds")
if not os.path.exists(SOUNDS_DIR):
    try:
        os.makedirs(SOUNDS_DIR, exist_ok=True)
    except Exception:
        pass

ICONS_DIR = os.path.join(APP_DIR, "icons")
if not os.path.exists(ICONS_DIR):
    try:
        os.makedirs(ICONS_DIR, exist_ok=True)
    except Exception:
        pass

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

def load_buttons():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    defaults = [
        {"id": "btn_1", "title": "Anterior", "theme": "theme-media", "type": "system", "action": "prev_track", "target": "", "icon": "prev"},
        {"id": "btn_2", "title": "Play / Pausa", "theme": "theme-media", "type": "system", "action": "play_pause", "target": "", "icon": "play_pause"},
        {"id": "btn_3", "title": "Siguiente", "theme": "theme-media", "type": "system", "action": "next_track", "target": "", "icon": "next"},
        {"id": "btn_4", "title": "Mutear", "theme": "theme-danger", "type": "system", "action": "vol_mute", "target": "", "icon": "mute"},
        {"id": "btn_5", "title": "Volumen -", "theme": "theme-sys", "type": "system", "action": "vol_down", "target": "", "icon": "vol_down"},
        {"id": "btn_6", "title": "Volumen +", "theme": "theme-sys", "type": "system", "action": "vol_up", "target": "", "icon": "vol_up"},
        {"id": "btn_7", "title": "Escritorio", "theme": "theme-sys", "type": "system", "action": "desktop", "target": "", "icon": "desktop"},
        {"id": "btn_8", "title": "Bloquear PC", "theme": "theme-danger", "type": "system", "action": "lock_pc", "target": "", "icon": "lock"},
        {"id": "btn_9", "title": "VS Code", "theme": "theme-dev", "type": "app", "action": "", "target": "code", "icon": "code"},
        {"id": "btn_10", "title": "Terminal", "theme": "theme-dev", "type": "app", "action": "", "target": "powershell", "icon": "terminal"},
        {"id": "btn_11", "title": "¡Ta-dá! 🎉", "theme": "theme-pink", "type": "sound", "action": "", "target": "tada.wav", "icon": "sound"},
        {"id": "btn_12", "title": "Calculadora", "theme": "theme-util", "type": "app", "action": "", "target": "calc", "icon": "calc"}
    ]
    save_buttons(defaults)
    return defaults

def save_buttons(buttons):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(buttons, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def list_sounds():
    if not os.path.exists(SOUNDS_DIR):
        return []
    valid_exts = {".mp3", ".wav", ".wma", ".ogg", ".m4a", ".aac"}
    files = []
    try:
        for f in os.listdir(SOUNDS_DIR):
            if os.path.splitext(f)[1].lower() in valid_exts:
                files.append(f)
    except Exception:
        pass
    return sorted(files)

sound_counter = 0

def play_sound(filename):
    global sound_counter
    if not filename:
        return False
    filepath = os.path.join(SOUNDS_DIR, filename)
    if not os.path.exists(filepath):
        if os.path.exists(filename):
            filepath = filename
        else:
            return False

    filepath = os.path.normpath(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".wav":
        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            pass

    try:
        # Cerrar dispositivos previos para liberar locks sobre archivos de audio
        ctypes.windll.winmm.mciSendStringW('close all', None, 0, None)
        sound_counter = (sound_counter + 1) % 50
        alias = f"sd_snd_{sound_counter}"
        ret = ctypes.windll.winmm.mciSendStringW(f'open "{filepath}" type mpegvideo alias {alias}', None, 0, None)
        if ret == 0:
            ctypes.windll.winmm.mciSendStringW(f'play {alias} from 0', None, 0, None)
            return True
    except Exception:
        pass
    return False

def stop_all_sounds():
    try:
        import winsound
        winsound.PlaySound(None, 0)
    except Exception:
        pass
    try:
        ctypes.windll.winmm.mciSendStringW('close all', None, 0, None)
        return True
    except Exception:
        return False

cached_apps = None

def list_installed_apps():
    global cached_apps
    if cached_apps is not None:
        return cached_apps

    builtin = [
        {"name": "🔢 Calculadora", "target": "calc", "icon": "calc", "category": "Herramientas de Windows"},
        {"name": "📝 Bloc de Notas", "target": "notepad", "icon": "📝", "category": "Herramientas de Windows"},
        {"name": "🎨 Paint", "target": "mspaint", "icon": "🎨", "category": "Herramientas de Windows"},
        {"name": "📁 Explorador de Archivos", "target": "explorer", "icon": "📁", "category": "Herramientas de Windows"},
        {"name": "💻 Terminal / PowerShell", "target": "powershell", "icon": "terminal", "category": "Herramientas de Windows"},
        {"name": "⚙️ Configuración de Windows", "target": "ms-settings:", "icon": "⚙️", "category": "Herramientas de Windows"},
        {"name": "📊 Administrador de Tareas", "target": "taskmgr", "icon": "📊", "category": "Herramientas de Windows"},
    ]
    seen = {b["name"].lower(): True for b in builtin}
    
    dirs = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
    ]
    ignore_words = {"uninstall", "desinstalar", "help", "ayuda", "readme", "leeme", "documentation", "manual", "website", "sitio", "web", "url"}
    installed = []

    for d in dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = f[:-4]
                        low = name.lower()
                        if any(w in low for w in ignore_words):
                            continue
                        if low in seen:
                            continue
                        seen[low] = True
                        full_p = os.path.join(root, f)
                        # Sugerir icono visual apropiado
                        icon = "🚀"
                        if any(k in low for k in ["code", "visual studio", "sublime", "dev", "git"]):
                            icon = "code"
                        elif any(k in low for k in ["discord", "chat", "slack", "teams"]):
                            icon = "💬"
                        elif any(k in low for k in ["spotify", "music", "audio", "itunes", "vlc"]):
                            icon = "🎵"
                        elif any(k in low for k in ["game", "steam", "epic", "riot", "blizzard", "play", "juego"]):
                            icon = "🎮"
                        elif any(k in low for k in ["chrome", "edge", "firefox", "brave", "opera", "browser"]):
                            icon = "🌐"
                        elif any(k in low for k in ["obs", "stream", "cam", "video", "twitch"]):
                            icon = "📺"
                        installed.append({
                            "name": name,
                            "target": full_p,
                            "icon": icon,
                            "category": "Programas Instalados"
                        })
    installed.sort(key=lambda x: x["name"].lower())
    cached_apps = builtin + installed
    return cached_apps

def launch_app(target):
    if not target:
        return False
    target = target.strip()
    if target.lower() == "code":
        code_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe")
        if os.path.exists(code_path):
            target = code_path

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    try:
        startupinfo.lpDesktop = r"WinSta0\Default"
    except Exception:
        pass

    # Metodo 1: audio_tool.exe nativo (.NET Process.Start con resolucion de .lnk y sesion interactiva)
    if os.path.exists(AUDIO_TOOL_PATH):
        try:
            subprocess.Popen([AUDIO_TOOL_PATH, "launch", target], startupinfo=startupinfo)
            return True
        except Exception:
            pass

    # Metodo 2: os.startfile nativo
    try:
        os.startfile(target)
        return True
    except Exception:
        pass

    # Metodo 3: ShellExecuteW
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(0, "open", target, None, None, 1)
        if ret > 32:
            return True
    except Exception:
        pass

    # Metodo 4: cmd start
    try:
        subprocess.Popen(f'cmd.exe /c start "" "{target}"', shell=True, startupinfo=startupinfo)
        return True
    except Exception:
        pass

    return False

def handle_action_request(data):
    action_type = data.get("type", "")
    action = data.get("action", "")
    target = data.get("target", "")

    if action == "stop_all_sounds" or action_type == "sound_stop":
        return stop_all_sounds()

    if action_type == "sound":
        return play_sound(target)

    elif action_type == "url":
        if target:
            if not target.startswith("http://") and not target.startswith("https://"):
                target = "https://" + target
            return launch_app(target)

    elif action_type == "app":
        if target:
            return launch_app(target)

    elif action_type == "hotkey":
        if target:
            run_audio_tool(f"hotkey {target}")
            return True

    elif action_type == "system":
        execute_action(action)
        return True

    if action:
        execute_action(action)
        return True

    return False

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
        launch_app("code")
    elif action == "open_terminal":
        launch_app("powershell")
    elif action == "open_browser":
        launch_app("http://localhost:5000")
    elif action == "open_calc":
        launch_app("calc")
    elif action == "stop_all_sounds":
        stop_all_sounds()
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

        if self.path == "/api/buttons":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(load_buttons(), ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/sounds":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(list_sounds(), ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/apps":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(list_installed_apps(), ensure_ascii=False).encode("utf-8"))
            return

        if self.path.startswith("/icons/"):
            icon_file = os.path.basename(self.path)
            full_path = os.path.join(ICONS_DIR, icon_file)
            if os.path.exists(full_path):
                ext = os.path.splitext(icon_file)[1].lower()
                mime = "image/png" if ext == ".png" else ("image/jpeg" if ext in [".jpg", ".jpeg"] else ("image/svg+xml" if ext == ".svg" else "application/octet-stream"))
                with open(full_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(data)
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
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if self.path == "/api/action":
            success = handle_action_request(payload)
            print(f"[ACTION] {payload} -> success={success}", flush=True)
            res = {"status": "ok" if success else "error"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path == "/api/buttons":
            buttons = payload.get("buttons", payload)
            if isinstance(buttons, list):
                save_buttons(buttons)
                res = {"status": "ok"}
            else:
                res = {"status": "error", "message": "Invalid buttons format"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if self.path == "/api/upload_sound":
            filename = payload.get("filename", "")
            b64data = payload.get("data", "")
            if filename and b64data:
                clean_name = os.path.basename(filename)
                clean_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)
                ext = os.path.splitext(clean_name)[1].lower()
                valid_exts = {".mp3", ".wav", ".wma", ".ogg", ".m4a", ".aac"}
                if ext in valid_exts:
                    dest_path = os.path.join(SOUNDS_DIR, clean_name)
                    already_exists = os.path.exists(dest_path)
                    try:
                        import base64
                        file_bytes = base64.b64decode(b64data)
                        # Liberar locks previos sobre mci
                        ctypes.windll.winmm.mciSendStringW('close all', None, 0, None)
                        try:
                            with open(dest_path, "wb") as f:
                                f.write(file_bytes)
                        except PermissionError:
                            # Si ya existe en disco y esta bloqueado por reproduccion, se reutiliza
                            pass
                        
                        msg = f"El archivo '{clean_name}' ya existe en la carpeta de sonidos y ha sido seleccionado." if already_exists else f"'{clean_name}' copiado con éxito a la carpeta sounds/."
                        res = {
                            "status": "ok",
                            "filename": clean_name,
                            "sounds": list_sounds(),
                            "already_existed": already_exists,
                            "message": msg
                        }
                    except Exception as e:
                        res = {"status": "error", "message": f"Error guardando archivo: {e}"}
                else:
                    res = {"status": "error", "message": "Formato no compatible (.mp3, .wav, .wma, .ogg, .m4a)"}
            else:
                res = {"status": "error", "message": "Datos incompletos"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        if self.path == "/api/upload_icon":
            filename = payload.get("filename", "")
            b64data = payload.get("data", "")
            if filename and b64data:
                clean_name = os.path.basename(filename)
                clean_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)
                ext = os.path.splitext(clean_name)[1].lower()
                valid_exts = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
                if ext in valid_exts:
                    dest_path = os.path.join(ICONS_DIR, clean_name)
                    try:
                        import base64
                        file_bytes = base64.b64decode(b64data)
                        with open(dest_path, "wb") as f:
                            f.write(file_bytes)
                        res = {"status": "ok", "url": f"/icons/{clean_name}", "filename": clean_name}
                    except Exception as e:
                        res = {"status": "error", "message": str(e)}
                else:
                    res = {"status": "error", "message": "Formato no soportado (usa PNG, JPG, SVG o WebP)"}
            else:
                res = {"status": "error", "message": "Faltan datos del archivo"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
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
        self.root.title("Stream Deck PC Server • por Gandalfs3")
        self.root.geometry("740x510")
        self.root.resizable(False, False)
        self.root.configure(bg="#0d1117")

        self.cloudflared_proc = None
        self.public_url = ""
        self.local_ip = get_local_ip()
        self.local_url = f"http://{self.local_ip}:{PORT}"
        self.current_qr_target = "local"
        self.qr_photo = None

        self.build_ui()
        self.switch_qr("local")
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
        badge_lbl.pack(side="left", padx=8)

        author_lbl = tk.Label(title_left, text="por @Gandalfs3", font=("Segoe UI", 9, "bold"), fg="#8b949e", bg="#21262d", padx=6, pady=1, cursor="hand2")
        author_lbl.pack(side="left", padx=2)
        author_lbl.bind("<Button-1>", lambda e: subprocess.Popen('start "" "https://github.com/Gandalfs3"', shell=True))

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

        # TARJETA 1: RED LOCAL WI-FI (RECOMENDADO EN CASA)
        card2 = tk.Frame(conn_frame, bg="#161b22", padx=16, pady=14, highlightbackground="#30363d", highlightthickness=1)
        card2.pack(fill="x", pady=(0, 14))

        card2_top = tk.Frame(card2, bg="#161b22")
        card2_top.pack(fill="x", pady=(0, 4))

        lbl_c2_title = tk.Label(card2_top, text="📶 Conexión Red Local (Wi-Fi)", font=("Segoe UI", 12, "bold"), fg="#7ee787", bg="#161b22")
        lbl_c2_title.pack(side="left")

        lbl_c2_rec = tk.Label(card2_top, text="RECOMENDADO (SIN LAG)", font=("Segoe UI", 8, "bold"), fg="#3fb950", bg="#161b22")
        lbl_c2_rec.pack(side="right")

        lbl_c2_desc = tk.Label(card2, text="Ideal si tu tablet y la PC están en el mismo Wi-Fi (conexión directa e instantánea):", font=("Segoe UI", 9), fg="#8b949e", bg="#161b22")
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

        self.btn_copy_loc = tk.Button(b2_frame, text="📋 Copiar IP Local", font=("Segoe UI", 9, "bold"), bg="#238636", fg="#ffffff", activebackground="#2ea043", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.copy_loc_url)
        self.btn_copy_loc.pack(side="left", padx=(0, 8))

        self.btn_open_loc = tk.Button(b2_frame, text="🌐 Abrir en esta PC", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.open_loc_browser)
        self.btn_open_loc.pack(side="left")

        # TARJETA 2: ENLACE PÚBLICO REMOTO (CLOUDFLARE)
        card1 = tk.Frame(conn_frame, bg="#161b22", padx=16, pady=14, highlightbackground="#30363d", highlightthickness=1)
        card1.pack(fill="x")

        card1_top = tk.Frame(card1, bg="#161b22")
        card1_top.pack(fill="x", pady=(0, 4))

        lbl_c1_title = tk.Label(card1_top, text="☁️ Enlace Remoto / Internet", font=("Segoe UI", 12, "bold"), fg="#58a6ff", bg="#161b22")
        lbl_c1_title.pack(side="left")

        lbl_c1_desc = tk.Label(card1, text="Usa este enlace si te conectas fuera de casa o desde datos móviles:", font=("Segoe UI", 9), fg="#8b949e", bg="#161b22")
        lbl_c1_desc.pack(anchor="w", pady=(0, 8))

        # URL Entry Remoto
        url_box1 = tk.Frame(card1, bg="#21262d", padx=8, pady=6, highlightbackground="#30363d", highlightthickness=1)
        url_box1.pack(fill="x", pady=(0, 10))

        self.url_pub_var = tk.StringVar(value="Generando túnel seguro...")
        self.entry_pub = tk.Entry(url_box1, textvariable=self.url_pub_var, font=("Consolas", 11, "bold"), fg="#3fb950", bg="#21262d", bd=0, readonlybackground="#21262d", state="readonly")
        self.entry_pub.pack(fill="x")

        # Botones Remoto
        b1_frame = tk.Frame(card1, bg="#161b22")
        b1_frame.pack(fill="x")

        self.btn_copy_pub = tk.Button(b1_frame, text="📋 Copiar Remoto", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.copy_pub_url)
        self.btn_copy_pub.pack(side="left", padx=(0, 8))

        self.btn_open_pub = tk.Button(b1_frame, text="🌐 Probar Remoto", font=("Segoe UI", 9), bg="#21262d", fg="#c9d1d9", activebackground="#30363d", activeforeground="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=self.open_pub_browser)
        self.btn_open_pub.pack(side="left")

        lbl_c1_hint = tk.Label(card1, text="⚠️ El túnel Cloudflare puede tardar 20-30 seg en propagar su DNS por primera vez.", font=("Segoe UI", 8), fg="#d29922", bg="#161b22")
        lbl_c1_hint.pack(anchor="w", pady=(8, 0))

        # 3. PIE DE PAGINA
        footer_frame = tk.Frame(self.root, bg="#0d1117", padx=20, pady=8)
        footer_frame.pack(fill="x", side="bottom")

        lbl_footer = tk.Label(footer_frame, text="💡 Creado por Gandalfs3 • Código Abierto:", font=("Segoe UI", 8), fg="#8b949e", bg="#0d1117")
        lbl_footer.pack(side="left")

        link_gh = tk.Label(footer_frame, text="github.com/Gandalfs3/streamdeck_local", font=("Segoe UI", 8, "underline"), fg="#58a6ff", bg="#0d1117", cursor="hand2")
        link_gh.pack(side="left", padx=(4, 0))
        link_gh.bind("<Button-1>", lambda e: subprocess.Popen('start "" "https://github.com/Gandalfs3/streamdeck_local"', shell=True))

        lbl_hint = tk.Label(footer_frame, text="⛶ F11 = Pantalla Completa", font=("Segoe UI", 8), fg="#3fb950", bg="#0d1117")
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
    # Prevenir multiples instancias que puedan colisionar con el puerto o Cloudflare
    MUTEX_NAME = "StreamDeck_Local_SingleInstance_Mutex_Gandalfs3"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("Stream Deck en Ejecución", "Stream Deck ya se está ejecutando en tu PC.\nRevisa tus ventanas abiertas o la barra de tareas.")
        sys.exit(0)

    # Limpiar procesos huérfanos anteriores
    try:
        subprocess.run("taskkill /f /im cloudflared.exe 2>nul", shell=True)
    except Exception:
        pass

    get_stats()
    root = tk.Tk()
    app = StreamDeckApp(root)
    root.mainloop()
