# Overcast OpenVPN Client

A lightweight, high-performance Windows desktop application that dynamically fetches, pings, and routes public VPN nodes using the VPNGate API and native OpenVPN core utilities. 

Built completely in Python using an asynchronous, multi-threaded Tkinter interface, this client features native dark-theme styling, automated dependency bootstrapping, a custom single-file binary auto-update system via GitHub, and strict DNS/IPv6 leak protections.

---

## 🚀 Key Features

* **Single-File Executable Portability:** The entire application runtime, Python interpreter, and graphical framework assets are bundled into a solitary, standalone executable binary (`OvercastVPN.exe`) with zero local directory dependencies.
* **Auto-Dependency Bootstrapper:** Detects if the OpenVPN core binary (`openvpn.exe`) is installed on the host system. If missing, it spawns an integrated download modal tracking the official community MSI setup, triggers the installation wizard, and dynamically maps the binary folder directly to the machine-wide Registry environment path.
* **High-Reliability Leak Protection:** Injects rigorous routing constraints natively into OpenVPN configs including `redirect-gateway def1 bypass-dhcp`, `block-outside-dns`, and `block-ipv6`. This completely neutralizes Windows Smart Multi-Homed Name Resolution leaks over unencrypted local gateways.
* **Multi-Threaded Asynchronous Core:** Keeps the GUI highly responsive. Latency testing sweeps run concurrently across a dedicated execution pool thread-limiting network tasks, preventing interface freezes during refresh sweeps.
* **Persistent Favorites & Caching System:** Local state tracking records pinned servers and latency metadata locally into isolated JSON cache models between application instances.
* **Binary-Level Auto-Updater (v1.0.2):** Automatically monitors your upstream GitHub branch metadata. If an update is detected, the app drops a transient system patcher into your computer's `TEMP` directory, shuts down the locked executable, streams down the fresh pre-compiled `.exe` directly from your GitHub Releases, overwrites the application, and hot-swaps the active process cleanly.

---

## 📂 Project Directory Architecture

```text
overcast-vpn-client/
│
├── .gitignore               # Excludes temporary application caches and session variables
├── LICENSE                  # Open-source MIT usage license
├── README.md                # Project documentation and guide
├── requirements.txt         # Minimal third-party library dependency mappings (for source compilation)
├── version.txt              # Production metadata tag read by the remote update system (v1.0.2)
│
└── src/                     # Core application source packages
    ├── __init__.py          # Package initializer
    ├── main.py              # Application entry point (handles UAC/update orchestrations)
    ├── core.py              # System-level code (UAC, path validation, VPN lifecycle)
    ├── ui.py                # Tkinter View components (Main Frame & progress windows)
    └── updater.py           # Independent background binary release patch manager

```

---

## 🛠️ Installation & Setup

### For End Users (Standalone Executable)

1. Head over to the **Releases** tab on this GitHub repository.
2. Download the latest compiled **`OvercastVPN.exe`**.
3. Move it to your Desktop, right-click, and select **Run as Administrator** (or accept the automated UAC prompt).

### For Developers (Running from Source)

1. **Clone the repository:**

```bash
   git clone https://github.com/eqvx/overcast.git
   cd overcast

```

2. **Install external library requirements:**

```bash
   pip install -r requirements.txt

```

3. **Launch the Client:**

```bash
   python src/main.py

```

4. **Freeze into a Standalone Binary:**
To build your own single-file `.exe` build using PyInstaller, run:

```bash
   pyinstaller --noconfirm --onefile --windowed --uac-admin --name "OvercastVPN" --paths "src" src/main.py

```

> ⚠️ **Administrative Privileges Notice:** Because this application programmatically adjusts global system network routing metrics, edits the Windows Registry `PATH` variable, and controls underlying OpenVPN TAP network adapters, it **must run with Administrator privileges**. The application will automatically prompt a User Account Control (UAC) elevation window on startup if it isn't already running in an elevated shell.

---

## ⚙️ How the Auto-Update System Works

This repository is configured with a fully automated binary deployment engine:

1. When a client fires up `OvercastVPN.exe`, it inspects its internal compilation version signature (`v1.0.2`) against the raw text format inside the upstream repository's `version.txt`.
2. If a mismatch is tracked, it opens a prompt to confirm the patch.
3. The app writes a small, self-contained worker script into your machine's `TEMP` directory and closes the main executable to unlock the file handle.
4. The background patcher streams down the new precompiled binary directly from your repository's **GitHub Releases payload target**, deletes the old version, replaces it, boots up the refreshed client instance, and completely deletes itself.

---

## 📄 License

This project is licensed under the terms of the MIT License. View the [LICENSE](https://www.google.com/search?q=LICENSE) file for authorization guidelines.
