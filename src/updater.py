import os
import sys
import time
import subprocess
import requests
from tkinter import messagebox

# CHANGE THESE to match your actual GitHub username and repository name
GITHUB_USER = "yourusername"
GITHUB_REPO = "overcast-vpn-client"

VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.txt"
RAW_SRC_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/src/"

TEMP_DIR = os.environ.get('TEMP', os.getcwd())
UPDATER_SCRIPT_PATH = os.path.join(TEMP_DIR, "overcast_patcher.py")

def check_for_updates(current_version: str) -> bool:
    """Queries GitHub for the latest version string and handles the update sequence if a mismatch is found."""
    try:
        response = requests.get(VERSION_URL, timeout=5)
        if response.status_code != 200:
            return False
            
        latest_version = response.text.strip()
        if latest_version == current_version:
            return False # Already running the latest build

        # Prompt the user to update
        choice = messagebox.askyesno(
            "Update Available", 
            f"A newer version ({latest_version}) of Overcast Client is available.\nWould you like to auto-update and restart now?"
        )
        if not choice:
            return False

        # Build a lightweight independent Python script in the Temp directory to orchestrate the overwrite
        _write_detached_patcher_script()
        
        # Launch the detached patcher process
        subprocess.Popen([sys.executable, UPDATER_SCRIPT_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # Kill the current application cleanly so the file locks are released
        sys.exit(0)
        
    except Exception as e:
        print(f"[Updater Warning] Update check bypassed: {e}")
        return False

def _write_detached_patcher_script():
    """Generates an ephemeral bootstrap python script capable of overriding the master files from outside the app domain."""
    # Escape local paths to pass safely into the generated script string
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_dir = os.path.join(root_dir, "src")
    main_py = os.path.join(src_dir, "main.py")

    script_content = f"""import os
import sys
import time
import requests
import subprocess

time.sleep(1.5) # Give the parent process breathing room to completely exit and lift file locks

# Targeted source structural updates
modules = ["core.py", "ui.py", "main.py"]
base_url = "{RAW_SRC_URL}"
target_dir = r"{src_dir}"

success = True
for mod in modules:
    try:
        res = requests.get(base_url + mod, timeout=10)
        if res.status_code == 200:
            with open(os.path.join(target_dir, mod), "w", encoding="utf-8") as f:
                f.write(res.text)
        else:
            success = False
    except Exception:
        success = False

if success:
    # Relaunch the master process securely under elevated permission tokens
    subprocess.Popen([sys.executable, r"{main_py}"], shell=True)

# Delete this patcher tool smoothly
try:
    os.remove(__file__)
except Exception:
    pass
"""
    with open(UPDATER_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(script_content)