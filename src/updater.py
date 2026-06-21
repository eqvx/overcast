import os
import sys
import subprocess
import requests
from tkinter import messagebox

VERSION_URL = f"https://raw.githubusercontent.com/eqvx/overcast/main/version.txt"
BINARY_DIST_URL = f"https://github.com/eqvx/overcast/releases/latest/download/OvercastVPN.exe"

TEMP_DIR = os.environ.get('TEMP', os.getcwd())
UPDATER_SCRIPT_PATH = os.path.join(TEMP_DIR, "overcast_binary_patcher.py")

def check_for_updates(current_version: str) -> bool:
    try:
        response = requests.get(VERSION_URL, timeout=5)
        if response.status_code != 200:
            return False
            
        latest_version = response.text.strip()
        if latest_version == current_version:
            return False

        choice = messagebox.askyesno(
            "Update Available", 
            f"A newer version ({latest_version}) of Overcast Client is available.\nWould you like to auto-update and restart now?"
        )
        if not choice:
            return False

        # Get the path of the currently running single-file executable
        current_exe_path = sys.executable
        
        # Write the binary patcher script to the TEMP directory
        _write_binary_patcher_script(current_exe_path)
        
        # Launch the detached binary patcher
        subprocess.Popen([sys.executable, UPDATER_SCRIPT_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # Immediate exit to free up the executable lock file so it can be replaced
        sys.exit(0)
        
    except Exception as e:
        print(f"[Updater Warning] Update check bypassed: {e}")
        return False

def _write_binary_patcher_script(target_exe_path: str):
    """Generates an external script that downloads the new compiled binary and overwrites the active executable."""
    script_content = f"""import os
import sys
import time
import requests
import subprocess

time.sleep(2.0) # Wait for parent executable file handle lock to lift safely

target_exe = r"{target_exe_path}"
download_url = "{BINARY_DIST_URL}"

try:
    # Stream download the new compiled binary
    res = requests.get(download_url, timeout=30, stream=True)
    if res.status_code == 200:
        # Save to a temporary location first
        temp_exe = target_exe + ".tmp"
        with open(temp_exe, "wb") as f:
            for chunk in res.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    
        # Overwrite the old executable binary file cleanly
        if os.path.exists(temp_exe):
            if os.path.exists(target_exe):
                os.remove(target_exe)
            os.rename(temp_exe, target_exe)
            
            # Spin up the brand-new updated application instance securely
            subprocess.Popen([target_exe], shell=True)
except Exception as e:
    pass

# Self-destruct patcher script
try:
    os.remove(__file__)
except Exception:
    pass
"""
    with open(UPDATER_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script_content)