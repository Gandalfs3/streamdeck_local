using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
    int RegisterControlChangeNotify(IntPtr pNotify);
    int UnregisterControlChangeNotify(IntPtr pNotify);
    int GetChannelCount(out uint pnChannelCount);
    int SetMasterVolumeLevel(float fLevelDB, IntPtr pguidEventContext);
    int SetMasterVolumeLevelScalar(float fLevel, IntPtr pguidEventContext);
    int GetMasterVolumeLevel(out float pfLevelDB);
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetChannelVolumeLevel(uint nChannel, float fLevelDB, IntPtr pguidEventContext);
    int SetChannelVolumeLevelScalar(uint nChannel, float fLevel, IntPtr pguidEventContext);
    int GetChannelVolumeLevel(uint nChannel, out float pfLevelDB);
    int GetChannelVolumeLevelScalar(uint nChannel, out float pfLevel);
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, IntPtr pguidEventContext);
    int GetMute([MarshalAs(UnmanagedType.Bool)] out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
    int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int f();
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject { }

class Program {
    [DllImport("user32.dll")]
    static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);

    [DllImport("user32.dll")]
    static extern uint MapVirtualKey(uint uCode, uint uMapType);

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr OpenWindowStationW([MarshalAs(UnmanagedType.LPWStr)] string lpszWinSta, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool SetProcessWindowStation(IntPtr hWinSta);

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr OpenDesktopW([MarshalAs(UnmanagedType.LPWStr)] string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool SetThreadDesktop(IntPtr hDesktop);

    static bool IsExtendedKey(byte vk) {
        return vk == 0x5B || vk == 0x5C || // Win
               vk == 0x26 || vk == 0x28 || vk == 0x25 || vk == 0x27 || // Arrows
               vk == 0x24 || vk == 0x23 || vk == 0x21 || vk == 0x22 || // Home, End, PgUp, PgDn
               vk == 0x2D || vk == 0x2E || // Ins, Del
               vk == 0x2C || // PrintScreen
               vk == 0xA3 || vk == 0xA5;   // RCtrl, RAlt
    }

    static byte ParseKey(string k) {
        k = k.Trim().ToLower();
        if (k == "ctrl" || k == "control") return 0x11;
        if (k == "shift") return 0x10;
        if (k == "alt") return 0x12;
        if (k == "win" || k == "windows" || k == "cmd" || k == "super") return 0x5B;
        if (k == "enter" || k == "return" || k == "intro") return 0x0D;
        if (k == "esc" || k == "escape") return 0x1B;
        if (k == "space" || k == "espacio") return 0x20;
        if (k == "tab" || k == "tabulador") return 0x09;
        if (k == "backspace" || k == "retroceso") return 0x08;
        if (k == "del" || k == "delete" || k == "supr" || k == "suprimir") return 0x2E;
        if (k == "ins" || k == "insert" || k == "insertar") return 0x2D;
        if (k == "home" || k == "inicio") return 0x24;
        if (k == "end" || k == "fin") return 0x23;
        if (k == "pageup" || k == "pgup" || k == "repag") return 0x21;
        if (k == "pagedown" || k == "pgdn" || k == "avpag") return 0x22;
        if (k == "up" || k == "arriba") return 0x26;
        if (k == "down" || k == "abajo") return 0x28;
        if (k == "left" || k == "izquierda") return 0x25;
        if (k == "right" || k == "derecha") return 0x27;
        if (k == "prtscr" || k == "printscreen" || k == "imprpant") return 0x2C;
        if (k.StartsWith("f") && k.Length > 1) {
            int fNum;
            if (int.TryParse(k.Substring(1), out fNum) && fNum >= 1 && fNum <= 24) {
                return (byte)(0x6F + fNum);
            }
        }
        if (k.Length == 1) {
            char c = char.ToUpper(k[0]);
            if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')) {
                return (byte)c;
            }
        }
        return 0;
    }

    static void SendHotkey(string combo) {
        string[] parts = combo.Split(new char[] { '+', '-', ' ' }, StringSplitOptions.RemoveEmptyEntries);
        var keys = new System.Collections.Generic.List<byte>();
        foreach (var p in parts) {
            byte vk = ParseKey(p);
            if (vk != 0) keys.Add(vk);
        }
        if (keys.Count == 0) return;

        for (int i = 0; i < keys.Count; i++) {
            byte vk = keys[i];
            uint scan = MapVirtualKey(vk, 0);
            uint flags = IsExtendedKey(vk) ? 1u : 0u;
            keybd_event(vk, (byte)scan, flags, 0);
            System.Threading.Thread.Sleep(10);
        }
        System.Threading.Thread.Sleep(40);
        for (int i = keys.Count - 1; i >= 0; i--) {
            byte vk = keys[i];
            uint scan = MapVirtualKey(vk, 0);
            uint flags = 2u | (IsExtendedKey(vk) ? 1u : 0u);
            keybd_event(vk, (byte)scan, flags, 0);
            System.Threading.Thread.Sleep(10);
        }
        Console.WriteLine("Atajo enviado: " + combo);
    }

    static IAudioEndpointVolume GetVolume() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var IID = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume aev;
        dev.Activate(ref IID, 23, 0, out aev);
        return aev;
    }

    static void Main(string[] args) {
        if (args.Length == 0) return;

        try {
            IntPtr hwinsta = OpenWindowStationW("WinSta0", false, 0x10000000);
            if (hwinsta != IntPtr.Zero) SetProcessWindowStation(hwinsta);
            IntPtr hdesk = OpenDesktopW("Default", 0, false, 0x10000000);
            if (hdesk != IntPtr.Zero) SetThreadDesktop(hdesk);
        } catch { }

        string fullArgs = string.Join(" ", args).Trim();
        string cmd = args[0].ToLower();

        try {
            if (cmd == "up") {
                var vol = GetVolume();
                float v;
                vol.GetMasterVolumeLevelScalar(out v);
                vol.SetMasterVolumeLevelScalar(Math.Min(1.0f, v + 0.08f), IntPtr.Zero);
                Console.WriteLine("Volumen subido a: " + Math.Round((v + 0.08f) * 100) + "%");
            }
            else if (cmd == "down") {
                var vol = GetVolume();
                float v;
                vol.GetMasterVolumeLevelScalar(out v);
                vol.SetMasterVolumeLevelScalar(Math.Max(0.0f, v - 0.08f), IntPtr.Zero);
                Console.WriteLine("Volumen bajado a: " + Math.Round((v - 0.08f) * 100) + "%");
            }
            else if (cmd == "mute") {
                var vol = GetVolume();
                bool m;
                vol.GetMute(out m);
                vol.SetMute(!m, IntPtr.Zero);
                Console.WriteLine("Mute cambiado a: " + (!m));
            }
            else if (cmd == "desktop") {
                Type shellType = Type.GetTypeFromProgID("Shell.Application");
                dynamic shell = Activator.CreateInstance(shellType);
                shell.ToggleDesktop();
                Console.WriteLine("Escritorio conmutado con exito");
            }
            else if (cmd == "launch" && args.Length > 1) {
                string target = string.Join(" ", args, 1, args.Length - 1).Trim();
                if (target.StartsWith("\"") && target.EndsWith("\"") && target.Length >= 2) {
                    target = target.Substring(1, target.Length - 2).Trim();
                }

                // Si es un acceso directo (.lnk), resolver destino real via WScript.Shell
                if (target.EndsWith(".lnk", StringComparison.OrdinalIgnoreCase) && System.IO.File.Exists(target)) {
                    try {
                        Type wscriptType = Type.GetTypeFromProgID("WScript.Shell");
                        if (wscriptType != null) {
                            dynamic wscript = Activator.CreateInstance(wscriptType);
                            dynamic shortcut = wscript.CreateShortcut(target);
                            string resolvedPath = (string)shortcut.TargetPath;
                            string resolvedArgs = (string)shortcut.Arguments;
                            string resolvedDir = (string)shortcut.WorkingDirectory;
                            if (!string.IsNullOrEmpty(resolvedPath)) {
                                System.Diagnostics.ProcessStartInfo psiLnk = new System.Diagnostics.ProcessStartInfo();
                                psiLnk.FileName = resolvedPath;
                                if (!string.IsNullOrEmpty(resolvedArgs)) psiLnk.Arguments = resolvedArgs;
                                if (!string.IsNullOrEmpty(resolvedDir) && System.IO.Directory.Exists(resolvedDir)) {
                                    psiLnk.WorkingDirectory = resolvedDir;
                                }
                                psiLnk.UseShellExecute = true;
                                System.Diagnostics.Process.Start(psiLnk);
                                Console.WriteLine("Lanzado acceso directo resuelto: " + resolvedPath);
                                return;
                            }
                        }
                    } catch (Exception exLnk) {
                        Console.WriteLine("Aviso resolviendo lnk: " + exLnk.Message);
                    }
                }

                try {
                    System.Diagnostics.ProcessStartInfo psi = new System.Diagnostics.ProcessStartInfo();
                    psi.FileName = target;
                    psi.UseShellExecute = true;
                    System.Diagnostics.Process.Start(psi);
                    Console.WriteLine("Lanzado con exito via Process.Start: " + target);
                } catch (Exception ex) {
                    Console.WriteLine("Error Process.Start: " + ex.Message);
                    try {
                        Type shellType = Type.GetTypeFromProgID("Shell.Application");
                        dynamic shell = Activator.CreateInstance(shellType);
                        shell.ShellExecute(target, "", "", "open", 1);
                        Console.WriteLine("Lanzado con exito via Shell.Application: " + target);
                    } catch (Exception ex2) {
                        Console.WriteLine("Error Shell.Application: " + ex2.Message);
                    }
                }
            }
            else if (cmd == "play_pause") {
                keybd_event(0xB3, 0, 1, 0);
                keybd_event(0xB3, 0, 3, 0);
                Console.WriteLine("Play/Pausa enviado");
            }
            else if (cmd == "next") {
                keybd_event(0xB0, 0, 1, 0);
                keybd_event(0xB0, 0, 3, 0);
            }
            else if (cmd == "prev") {
                keybd_event(0xB1, 0, 1, 0);
                keybd_event(0xB1, 0, 3, 0);
            }
            else if (cmd == "hotkey" || cmd.StartsWith("hotkey ") || fullArgs.StartsWith("hotkey", StringComparison.OrdinalIgnoreCase)) {
                string combo = "";
                if (cmd == "hotkey" && args.Length > 1) {
                    combo = string.Join(" ", args, 1, args.Length - 1).Trim().ToLower();
                } else if (fullArgs.Length > 6) {
                    combo = fullArgs.Substring(6).Trim().ToLower();
                }
                if (!string.IsNullOrEmpty(combo)) {
                    SendHotkey(combo);
                }
            }
        } catch (Exception ex) {
            Console.WriteLine("Error: " + ex.Message);
        }
    }
}
