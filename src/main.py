#!/usr/bin/env python3
import sys
from core import VPNManager, elevate_privileges, verify_and_fix_openvpn_path
from ui import InstallerProgressModal, VPNApp
from updater import check_for_updates

# Define local release version mapping metric
__VERSION__ = "1.0.0"

def launch_download_modal(url, target_path):
    """Callback bridge allowing core to spawn the download UI window."""
    modal = InstallerProgressModal(url, target_path)
    modal.mainloop()
    return modal.success

if __name__ == "__main__":
    # Ensure the script is running with elevated privileges
    elevate_privileges()
    
    # 1. Fire off the automated source update sequence check
    check_for_updates(__VERSION__)
    
    # 2. Flush legacy zombie OpenVPN tasks from previous sessions
    VPNManager.kill_all_openvpn()
    
    # 3. Verify environment pathways and prompt installer if needed
    verify_and_fix_openvpn_path(launch_download_modal)
    
    # 4. Build and initialize the main interface window
    app = VPNApp()
    app.mainloop()