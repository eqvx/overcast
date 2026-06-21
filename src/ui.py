import os
import re
import json
import csv
import threading
import subprocess
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from core import VPNGATE_API_URL, CACHE_JSON_PATH, FAVORITES_JSON_PATH, VPNManager

class InstallerProgressModal(tk.Tk):
    def __init__(self, download_url, save_path):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path
        self.success = False
        
        self.title("Overcast Environment Setup")
        self.geometry("450x150")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        self.lbl_info = tk.Label(self, text="Downloading official OpenVPN core binaries...", bg="#1e1e1e", fg="#e1e1e1")
        self.lbl_info.pack(pady=(25, 10))
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Installer.Horizontal.TProgressbar", troughcolor="#252526", background="#007acc")
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=380, mode="determinate", style="Installer.Horizontal.TProgressbar")
        self.progress.pack(pady=5)
        
        self.lbl_pct = tk.Label(self, text="0%", bg="#1e1e1e", fg="#9cdcfe", font=("Segoe UI", 9, "bold"))
        self.lbl_pct.pack()
        
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        try:
            response = requests.get(self.download_url, stream=True, timeout=20)
            total_size = int(response.headers.get('content-length', 0))
            bytes_written = 0
            with open(self.save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        bytes_written += len(chunk)
                        if total_size > 0:
                            percent = int((bytes_written / total_size) * 100)
                            self.after(0, lambda p=percent: self._update_ui(p))
            self.success = True
            self.after(0, self.destroy)
        except Exception as e:
            self.after(0, lambda err=e: self._handle_error(err))

    def _update_ui(self, percent):
        self.progress['value'] = percent
        self.lbl_pct.config(text=f"{percent}%")

    def _handle_error(self, error):
        messagebox.showerror("Download Failed", f"An error occurred while downloading OpenVPN:\n{error}")
        self.destroy()


class VPNApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Overcast OpenVPN Client")
        self.geometry("950x580")  
        self.configure(bg="#1e1e1e")
        
        self.vpn_manager = VPNManager()
        self.servers = []
        self.favorites = {}  
        self.ping_threads_limit = threading.Semaphore(15)  
        self.ping_session_id = 0
        self.completed_pings = 0
        self.is_connecting_manually = False

        self._load_favorites_from_disk()
        self._apply_dark_theme()
        self._build_ui()
        self._build_context_menu()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(200, self.load_cached_servers)

    def _apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#1e1e1e", foreground="#e1e1e1", font=("Segoe UI", 10))
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#e1e1e1", padding=(10, 4))
        style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")], foreground=[("selected", "#ffffff")])
        style.configure("TButton", background="#2d2d2d", foreground="#e1e1e1", padding=6)
        style.map("TButton", background=[("active", "#3e3e3e"), ("disabled", "#151515")], foreground=[("disabled", "#666666")])
        style.configure("Treeview", background="#252526", foreground="#ffffff", fieldbackground="#252526", rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background="#2d2d30", foreground="#e1e1e1", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

    def _build_ui(self):
        ctrl_panel = ttk.Frame(self, padding=12)
        ctrl_panel.pack(fill=tk.X)

        self.btn_refresh = ttk.Button(ctrl_panel, text="🔄 Fetch New Servers", command=self.fetch_servers)
        self.btn_refresh.pack(side=tk.LEFT, padx=4)

        self.btn_reping = ttk.Button(ctrl_panel, text="⚡ Re-Ping Current List", command=lambda: self.start_live_ping_orchestrator(None), state=tk.DISABLED)
        self.btn_reping.pack(side=tk.LEFT, padx=4)

        self.btn_connect = ttk.Button(ctrl_panel, text="▶ Connect", command=self._action_top_panel_connect)
        self.btn_connect.pack(side=tk.LEFT, padx=4)

        self.btn_disconnect = ttk.Button(ctrl_panel, text="■ Disconnect", command=self.action_disconnect, state=tk.DISABLED)
        self.btn_disconnect.pack(side=tk.LEFT, padx=4)

        self.lbl_status = tk.Label(ctrl_panel, text="Status: Idle System", bg="#1e1e1e", fg="#9cdcfe", font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT, padx=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.tab_all = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_all, text="🌐 All Public Nodes")
        self.tree_all = self._create_treeview(self.tab_all)
        self.tree_all.bind("<Button-3>", lambda e: self._show_context_menu(e, self.tree_all))

        self.tab_fav = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_fav, text="⭐ Starred Favorites")
        self.tree_fav = self._create_treeview(self.tab_fav)
        self.tree_fav.bind("<Button-3>", lambda e: self._show_context_menu(e, self.tree_fav))

    def _create_treeview(self, parent_frame):
        columns = ("country", "ip", "ping", "speed", "uptime")
        tree = ttk.Treeview(parent_frame, columns=columns, show="headings", selectmode="browse")
        
        tree.heading("country", text=" 📍 Target Region", command=lambda: self.sort_column(tree, "country", False))
        tree.heading("ip", text=" 🌐 Server Endpoint", command=lambda: self.sort_column(tree, "ip", False))
        tree.heading("ping", text=" ⏱ Live Latency", command=lambda: self.sort_column(tree, "ping", False))
        tree.heading("speed", text=" 🚀 Declared Bandwidth", command=lambda: self.sort_column(tree, "speed", False))
        tree.heading("uptime", text=" 🔄 Node Uptime", command=lambda: self.sort_column(tree, "uptime", False))

        tree.column("country", width=220, anchor=tk.W)
        tree.column("ip", width=160, anchor=tk.CENTER)
        tree.column("ping", width=120, anchor=tk.CENTER)
        tree.column("speed", width=130, anchor=tk.CENTER)
        tree.column("uptime", width=120, anchor=tk.CENTER)

        tree.tag_configure("good", foreground="#4ec9b0", font=("Segoe UI", 10, "bold"))     
        tree.tag_configure("medium", foreground="#dcdcaa")   
        tree.tag_configure("bad", foreground="#f44747")      
        tree.tag_configure("pinging", foreground="#808080")  

        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def _get_active_tab_tree(self):
        current_tab_index = self.notebook.index(self.notebook.select())
        return self.tree_all if current_tab_index == 0 else self.tree_fav

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2d2d30", fg="#e1e1e1", activebackground="#007acc", activeforeground="#ffffff")
        self.context_menu.add_command(label="Connect", command=self._context_action_connect_toggle)
        self.context_menu.add_command(label="Favorite", command=self._context_action_fav_toggle)

    def _show_context_menu(self, event, active_tree):
        row_id = active_tree.identify_row(event.y)
        if not row_id: return
        
        active_tree.selection_set(row_id)
        self.target_tree_context = active_tree
        self.target_row_context_id = row_id
        
        values = active_tree.item(row_id, "values")
        server_ip = values[1]
        
        if self.vpn_manager.current_connected_ip == server_ip:
            self.context_menu.entryconfigure(0, label="■ Disconnect From Server", command=self.action_disconnect)
        else:
            self.context_menu.entryconfigure(0, label="▶ Connect To Server", command=self._context_action_connect_toggle)

        if server_ip in self.favorites:
            self.context_menu.entryconfigure(1, label="❌ Remove from Favorites", command=self._context_action_fav_toggle)
        else:
            self.context_menu.entryconfigure(1, label="⭐ Add to Favorites", command=self._context_action_fav_toggle)
            
        self.context_menu.post(event.x_root, event.y_root)

    def _action_top_panel_connect(self):
        active_tree = self._get_active_tab_tree()
        selected_items = active_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Alert", "Please select a server row from the table below before clicking Connect.")
            return
        row_id = selected_items[0]
        values = active_tree.item(row_id, "values")
        self._execute_vpn_connection(values[1])

    def _context_action_connect_toggle(self):
        values = self.target_tree_context.item(self.target_row_context_id, "values")
        self._execute_vpn_connection(values[1])

    def _execute_vpn_connection(self, ip):
        server = next((s for s in self.servers if s["ip"] == ip), None)
        if not server: return
        
        self.is_connecting_manually = True
        self.lbl_status.config(text="Status: Routing via secure tunnel...", fg="#569cd6")
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_reping.config(state=tk.DISABLED)
        self.btn_connect.config(state=tk.DISABLED)
        self.btn_disconnect.config(state=tk.NORMAL)

        def success():
            self.is_connecting_manually = False
            self.lbl_status.config(text=f"Status: Active Tunnel ({server['country']})", fg="#4ec9b0")

        def fail(reason):
            self.is_connecting_manually = False
            self.lbl_status.config(text="Status: Link Terminated", fg="#f44747")
            self._reset_buttons()

        self.vpn_manager.connect(server["ip"], server["config"], success, fail)

    def _context_action_fav_toggle(self):
        values = self.target_tree_context.item(self.target_row_context_id, "values")
        ip = values[1]
        if ip in self.favorites: del self.favorites[ip]
        else: self.favorites[ip] = True
        self._save_favorites_to_disk()
        self.sync_trees_ui()

    def _load_favorites_from_disk(self):
        if os.path.exists(FAVORITES_JSON_PATH):
            try:
                with open(FAVORITES_JSON_PATH, "r", encoding="utf-8") as f:
                    self.favorites = json.load(f)
            except Exception: pass

    def _save_favorites_to_disk(self):
        try:
            with open(FAVORITES_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.favorites, f, indent=4)
        except Exception: pass

    def sync_trees_ui(self):
        self.tree_all.delete(*self.tree_all.get_children())
        self.tree_fav.delete(*self.tree_fav.get_children())

        for s in self.servers:
            ping_val = "Timed Out" if s["ping"] == 9999 else ("Measuring..." if s["ping"] == -1 else f"{s['ping']} ms")
            row_tag = "bad" if s["ping"] == 9999 else ("pinging" if s["ping"] == -1 else ("good" if s["ping"] < 90 else ("medium" if s["ping"] <= 220 else "bad")))
            
            display_country = f"⭐ {s['country']}" if s["ip"] in self.favorites else s["country"]
            row_values = (display_country, s["ip"], ping_val, s["speed"], s["uptime"])
            
            self.tree_all.insert("", tk.END, iid=f"all_{s['ip']}", values=row_values, tags=(row_tag,))
            if s["ip"] in self.favorites:
                self.tree_fav.insert("", tk.END, iid=f"fav_{s['ip']}", values=row_values, tags=(row_tag,))

    def load_cached_servers(self):
        if not os.path.exists(CACHE_JSON_PATH):
            self.fetch_servers()
            return
        try:
            with open(CACHE_JSON_PATH, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            self.servers.clear()
            for item in saved_data:
                self.servers.append({
                    "country": item["country"], "ip": item["ip"], "ping": item.get("ping", -1),
                    "speed": item["speed"], "uptime": item["uptime"], "config": item["config"]
                })
            self.sync_trees_ui()
            if self.servers:
                self.btn_reping.config(state=tk.NORMAL)
                self.start_live_ping_orchestrator(None)
        except Exception: self.fetch_servers()

    def fetch_servers(self):
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_reping.config(state=tk.DISABLED)
        self.btn_connect.config(state=tk.DISABLED)
        self.lbl_status.config(text="Status: Querying VPNGate API...", fg="#569cd6")
        
        def worker():
            try:
                res = requests.get(VPNGATE_API_URL, timeout=10)
                self._parse_raw_csv(res.text)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Handshake Error", f"Could not sync with remote nodes: {e}"))
                self.after(0, self._reset_buttons)
        threading.Thread(target=worker, daemon=True).start()

    def _parse_raw_csv(self, raw_data):
        lines = raw_data.split("\n")
        csv_data = [line for line in lines if not line.startswith("*") and line.strip()]
        reader = csv.DictReader(csv_data)
        
        self.servers.clear()
        seen_ips = set()
        for row in reader:
            if not row.get("IP") or row["IP"] in seen_ips: continue
            seen_ips.add(row["IP"])
            self.servers.append({
                "country": row["CountryLong"], "ip": row["IP"], "ping": -1,
                "speed": f"{float(row['Speed']) / 1000000:.1f} Mbps" if row["Speed"].isdigit() else "N/A",
                "uptime": f"{int(row['Uptime']) / 3600 / 24:.1f} days" if row["Uptime"].isdigit() else "N/A",
                "config": row["OpenVPN_ConfigData_Base64"]
            })
        self.sync_trees_ui()
        self._reset_buttons()
        self.btn_reping.config(state=tk.NORMAL)
        self.start_live_ping_orchestrator(None)

    def start_live_ping_orchestrator(self, target_list=None):
        self.ping_session_id += 1
        self.completed_pings = 0
        current_session = self.ping_session_id
        ping_targets = target_list if target_list is not None else self.servers
        if not ping_targets: return

        def ping_runner(server_item, session):
            with self.ping_threads_limit:
                if session != self.ping_session_id: return
                cmd = f"ping -n 1 -w 800 {server_item['ip']}"
                latency = 9999
                try:
                    out = subprocess.check_output(cmd, shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    match = re.search(r"time[=<](\d+)ms", out)
                    if match: latency = int(match.group(1))
                except Exception: pass
                server_item["ping"] = latency
                self.after(0, lambda: self._update_row_ping_ui(session, len(ping_targets)))

        for server in ping_targets:
            threading.Thread(target=ping_runner, args=(server, current_session), daemon=True).start()

    def _update_row_ping_ui(self, session, total):
        if session != self.ping_session_id: return
        self.completed_pings += 1
        if self.completed_pings == total:
            self.sync_trees_ui()
            try:
                with open(CACHE_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.servers, f, indent=4)
            except Exception: pass
            self.lbl_status.config(text="Status: Sync & Latency Sweep Finalized", fg="#4ec9b0")

    def sort_column(self, tree, col, reverse=False):
        l = [(tree.set(k, col), k) for k in tree.get_children("")]
        if col == "ping":
            l.sort(key=lambda e: 99999 if "Timed Out" in e[0] else (99998 if "Measuring" in e[0] else int(e[0].replace(" ms", ""))), reverse=reverse)
        elif col in ["speed", "uptime"]:
            l.sort(key=lambda t: [float(s) for s in re.findall(r"[-+]?\d*\.\d+|\d+", t[0])] or [0.0], reverse=reverse)
        else: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): tree.move(k, "", index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

    def action_disconnect(self):
        self.is_connecting_manually = False
        self.vpn_manager.disconnect()
        self.lbl_status.config(text="Status: Session Closed", fg="#e1e1e1")
        self.btn_disconnect.config(state=tk.DISABLED)
        self._reset_buttons()

    def _reset_buttons(self):
        self.btn_refresh.config(state=tk.NORMAL)
        self.btn_reping.config(state=tk.NORMAL)
        self.btn_connect.config(state=tk.NORMAL)

    def on_closing(self):
        self.vpn_manager.disconnect()
        self.destroy()