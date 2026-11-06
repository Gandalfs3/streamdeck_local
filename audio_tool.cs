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

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr OpenWindowStationW([MarshalAs(UnmanagedType.LPWStr)] string lpszWinSta, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool SetProcessWindowStation(IntPtr hWinSta);

    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr OpenDesktopW([MarshalAs(UnmanagedType.LPWStr)] string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);

    [DllImport("user32.dll", SetLastError = true)]
    static extern bool SetThreadDesktop(IntPtr hDesktop);

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
        } catch (Exception ex) {
            Console.WriteLine("Error: " + ex.Message);
        }
    }
}
