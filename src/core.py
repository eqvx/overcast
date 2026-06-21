import os
import sys
import base64
import signal
import threading
import subprocess
import ctypes
from tkinter import messagebox

VPNGATE_API_URL = "https://www.vpngate.net/api/iphone/"
OPENVPN_MSI_URL = "https://build.openvpn.net/downloads/releases/latest/openvpn-install-latest-amd64.msi"

TEMP_DIR = os.environ.get('TEMP', os.getcwd())
TEMP_OVPN_PATH = os.path.join(TEMP_DIR, "vpn_config.ovpn")
CACHE_JSON_PATH = os.path.join(TEMP_DIR, "vpngate_cache.json")
FAVORITES_JSON_PATH = os.path.join(TEMP_DIR, "vpngate_favorites.json")
TEMP_MSI_PATH = os.path.join(TEMP_DIR, "openvpn_setup.msi")

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate_privileges():
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)

def verify_and_fix_openvpn_path(modal_launcher_callback):
    standard_bin_dir = r"C:\Program Files\OpenVPN\bin"
    target_exe = os.path.join(standard_bin_dir, "openvpn.exe")
    
    if not os.path.exists(target_exe):
        response = messagebox.askyesno(
            "Dependency Missing", 
            "Looks like you don't have OpenVPN installed. Install it now?"
        )
        if not response:
            messagebox.showerror("Error", "OpenVPN is required for this client to operate. Exiting application.")
            sys.exit(0)
            
        success = modal_launcher_callback(OPENVPN_MSI_URL, TEMP_MSI_PATH)
        
        if not success or not os.path.exists(TEMP_MSI_PATH):
            messagebox.showerror("Error", "Installer download was incomplete. Exiting.")
            sys.exit(0)
            
        try:
            messagebox.showinfo("Installer Ready", "The OpenVPN setup will now open. Please complete the installation wizard to continue.")
            subprocess.run(["msiexec", "/i", TEMP_MSI_PATH], check=True)
        except Exception as e:
            messagebox.showerror("Installation Aborted", f"The installation wizard encountered an issue: {e}")
            sys.exit(0)
        finally:
            if os.path.exists(TEMP_MSI_PATH):
                try: os.remove(TEMP_MSI_PATH)
                except OSError: pass

        if not os.path.exists(target_exe):
            messagebox.showerror("Verification Failed", "OpenVPN executable could not be detected post-install. Exiting.")
            sys.exit(0)

    current_path = os.environ.get("PATH", "")
    if standard_bin_dir.lower() in current_path.lower():
        return

    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, 
            r"System\CurrentControlSet\Control\Session Manager\Environment", 
            0, winreg.KEY_ALL_ACCESS
        )
        raw_registry_path, _ = winreg.QueryValueEx(key, "Path")
        
        if standard_bin_dir.lower() not in raw_registry_path.lower():
            updated_registry_path = f"{raw_registry_path.rstrip(';')};{standard_bin_dir}"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated_registry_path)
            
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            os.environ["PATH"] = f"{current_path.rstrip(';')};{standard_bin_dir}"
            
        winreg.CloseKey(key)
    except Exception:
        os.environ["PATH"] = f"{current_path.rstrip(';')};{standard_bin_dir}"


class VPNManager:
    def __init__(self):
        self.process = None
        self.current_connected_ip = None

    @staticmethod
    def kill_all_openvpn():
        try:
            subprocess.run(["taskkill", "/F", "/IM", "openvpn.exe"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
        VPNManager.flush_dns_and_wfp()

    @staticmethod
    def flush_dns_and_wfp():
        try:
            subprocess.run(["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["netsh", "interface", "ip", "reset"], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass

    def connect(self, ip_address: str, config_base64: str, on_success, on_fail):
        self.disconnect()
        self.current_connected_ip = ip_address
        try:
            config_bytes = base64.b64decode(config_base64)
            config_text = config_bytes.decode('utf-8', errors='ignore')
            
            leak_protection_rules = (
                "\n"
                "# --- High-Reliability Leak Protection & Routing ---\n"
                "redirect-gateway def1 bypass-dhcp\n"
                "dhcp-option DNS 1.1.1.1\n"
                "dhcp-option DNS 1.0.0.1\n"
                "block-outside-dns\n"                  
                "block-ipv6\n"                         
                "register-dns\n"
                "route-metric 1\n"
                "route-delay 2\n"
                "ifconfig-nowarn\n"
            )
            config_text += leak_protection_rules
            
            with open(TEMP_OVPN_PATH, "w", encoding='utf-8') as f:
                f.write(config_text)
        except Exception as e:
            self.current_connected_ip = None
            on_fail(f"Failed to extract payload config: {e}")
            return

        def run():
            cmd = ["openvpn", "--config", TEMP_OVPN_PATH]
            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                )
                
                connected = False
                while self.process.poll() is None:
                    line = self.process.stdout.readline()
                    if not line: break
                    if "Initialization Sequence Completed" in line:
                        connected = True
                        on_success()
                        break
                    if "Cannot open TUN/TAP dev" in line or "Fatal" in line or "Error" in line:
                        break
                
                if not connected:
                    on_fail("Handshake initialization halted or failed.")
                    self.disconnect()
            except Exception as e:
                on_fail(f"Execution system fault: {e}")

        threading.Thread(target=run, daemon=True).start()

    def disconnect(self):
        self.current_connected_ip = None
        if self.process and self.process.poll() is None:
            try:
                os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
                self.process.wait(timeout=2)
            except Exception:
                try: self.process.kill()
                except Exception: pass
        self.process = None
        
        if os.path.exists(TEMP_OVPN_PATH):
            try: os.remove(TEMP_OVPN_PATH)
            except OSError: pass
            
        self.flush_dns_and_wfp()