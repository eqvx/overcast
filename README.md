# Overcast OpenVPN Client

A lightweight, high-performance Windows desktop application that dynamically fetches, pings, and routes public VPN nodes using the VPNGate API and native OpenVPN core utilities. 

Built completely in Python using an asynchronous, multi-threaded Tkinter interface, this client features native dark-theme styling, automated dependency bootstrapping, a custom split-file auto-update system via GitHub, and strict DNS/IPv6 leak protections.

---

## 🚀 Key Features

* **Auto-Dependency Bootstrapper:** Detects if the OpenVPN core binary (`openvpn.exe`) is installed on the host system. If missing, it spawns an integrated download modal tracking the official community MSI setup, triggers the installation wizard, and dynamically maps the binary folder directly to the machine-wide Registry environment path.
* **High-Reliability Leak Protection:** Injects rigorous routing constraints natively into OpenVPN configs including `redirect-gateway def1 bypass-dhcp`, `block-outside-dns`, and `block-ipv6`. This completely neutralizes Windows Smart Multi-Homed Name Resolution leaks over unencrypted local gateways.
* **Multi-Threaded Asynchronous Core:** Keeps the GUI highly responsive. Latency testing sweeps run concurrently across a dedicated execution pool thread-limiting network tasks, preventing interface freezes during refresh sweeps.
* **Persistent Favorites & Caching System:** Local state tracking records pinned servers and latency metadata locally into isolated JSON cache models between application instances.
* **Integrated Two-Stage Auto-Updater:** Automatically monitors your upstream GitHub branch metadata. If a version update is pushed, the app pulls the core files directly into a transient staging pipeline, updates the local files, and securely restarts the app context automatically.

---

## 📂 Project Directory Architecture

```text
overcast-vpn-client/
│
├── .gitignore               # Excludes temporary application caches and session variables
├── LICENSE                  # Open-source MIT usage license
├── README.md                # Project documentation and guide
├── requirements.txt         # Minimal third-party library dependency mappings
├── version.txt              # Production metadata tag read by the remote update system
│
└── src/                     # Core application packages
    ├── __init__.py          # Identifies src as an importable python module
    ├── main.py              # Main bootstrap runtime entry point (handles UAC/updates)
    ├── core.py              # System-level code (UAC, path validation, VPN lifecycle)
    ├── ui.py                # Tkinter View components (Main Frame & progress windows)
    └── updater.py           # Independent background deployment patch manager

```

---

## 🛠️ Installation & Setup

### Prerequisites

* **Operating System:** Windows 10 or 11 (64-bit).
* **Python Runtime:** Python 3.8 or higher installed on your system.

### Quick Start Guide

1. **Clone the repository:**
```bash
git clone [https://github.com/eqvx/overcast.git](https://github.com/eqvx/overcast.git)
cd overcast-vpn-client

```


2. **Install external library requirements:**
*(Note: Most modules used, like `tkinter`, `subprocess`, `ctypes`, and `winreg`, are natively bundled inside Python's Standard Library).*
```bash
pip install -r requirements.txt

```


3. **Launch the Client:**
```bash
python src/main.py

```



> ⚠️ **Administrative Privileges Notice:** Because this application programmatically adjusts global system network routing metrics, edits the Windows Registry `PATH` variable, and controls underlying OpenVPN TAP network adapters, it **must run with Administrator privileges**. The application will automatically prompt a User Account Control (UAC) elevation window on startup if it isn't already running in an elevated shell.

---

## ⚙️ How the Auto-Update System Works

This repository is configured with a fully automated, free code-patch deployment engine:

1. When a client fires up `src/main.py`, it inspects its local `__VERSION__` signature against the raw text format inside the upstream repository's `version.txt`.
2. If a mismatch is tracked, it opens a prompt to confirm the patch.
3. The app writes a small, self-contained worker thread script into your machine's `TEMP` directory and closes the main application to drop all file system locks.
4. The background patcher pulls down the updated copies of `main.py`, `core.py`, and `ui.py` directly from your GitHub master branch, overwrites the project contents, boots up the refreshed client instance, and completely deletes itself.

---

## 📄 License

This project is licensed under the terms of the MIT License. View the [LICENSE](https://www.google.com/search?q=LICENSE) file for authorization guidelines.