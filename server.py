import http.server
import json
import os
import subprocess
import ctypes
from ctypes import wintypes

PORT = 5000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
AUDIO_TOOL = os.path.join(DIRECTORY, "audio_tool.exe")

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

def run_audio_tool(cmd):
    if os.path.exists(AUDIO_TOOL):
        subprocess.Popen([AUDIO_TOOL, cmd], shell=False)

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

class StreamDeckHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps(get_stats())
            self.wfile.write(data.encode("utf-8"))
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/action":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                action = payload.get("action")
                self.execute_action(action)
                res = {"status": "ok", "action": action}
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

    def execute_action(self, action):
        print(f"[STREAM DECK] Accion ejecutada: {action}")
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
                subprocess.Popen(f'start "" "{code_path}"', shell=True)
            else:
                subprocess.Popen("start code", shell=True)
        elif action == "open_terminal":
            subprocess.Popen("start powershell", shell=True)
        elif action == "open_browser":
            subprocess.Popen("start http://localhost:3000", shell=True)
        elif action == "open_calc":
            subprocess.Popen("calc", shell=True)
        elif action == "lock_pc":
            ctypes.windll.user32.LockWorkStation()

if __name__ == "__main__":
    get_stats()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), StreamDeckHandler)
    print("==================================================")
    print("[OK] Stream Deck Server v4 (Native Audio Engine) listo!")
    print("==================================================")
    server.serve_forever()
