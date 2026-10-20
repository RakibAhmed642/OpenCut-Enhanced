"""
OpenCut Enhanced - Modern Minimal Yellow & White GUI Installer
Sleek, user-friendly, and autonomous installer for Adobe Premiere Pro CEP extension.
Supports:
  - 1-Click Auto Clone / Download from GitHub
  - Registry PlayerDebugMode Configuration (CSXS 9-18)
  - Adobe CEP Panel Installation
  - Desktop Shortcut Creation with Multi-Resolution Icon
  - Environment & Python Engine Verification
"""

import os
import sys
import shutil
import zipfile
import subprocess
import threading
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Constants & GitHub Endpoints
GITHUB_REPO_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced"
GITHUB_ZIP_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced/archive/refs/heads/main.zip"
GITHUB_GIT_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced.git"

APPDATA = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
ADOBE_CEP_DIR = Path(APPDATA) / "Adobe" / "CEP" / "extensions"
TARGET_EXT_DIR = ADOBE_CEP_DIR / "com.opencut.panel"

# Color Palette: Deep Slate/Charcoal base with Crisp White and Vibrant Yellow Accents
BG_DARK = "#0b0f19"         # Deep Slate background
CARD_BG = "#131b2e"         # Elevated Card background
CARD_INNER = "#1e293b"      # Inner container background
ACCENT_YELLOW = "#facc15"   # Vibrant Gold / Yellow
YELLOW_HOVER = "#eab308"    # Darker Yellow on hover
TEXT_WHITE = "#ffffff"      # Crisp White
TEXT_MUTED = "#94a3b8"      # Soft Slate Gray
BORDER_COLOR = "#1e293b"    # Subtle Border

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def get_resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def get_default_install_dir() -> Path:
    base = get_base_dir()
    # If installer is executed inside an existing cloned repo
    if (base / "extension" / "com.opencut.panel" / "CSXS" / "manifest.xml").exists():
        return base
    # Otherwise install cleanly into user's home directory
    return Path.home() / "OpenCut-Enhanced"

class OpenCutMinimalInstaller:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OpenCut Enhanced — 1-Click Installer")
        self.root.geometry("600x520")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        self.install_dir = get_default_install_dir()
        self.is_installing = False
        self.install_succeeded = False

        self._set_window_icon()
        self._apply_styles()
        self._build_ui()

    def _set_window_icon(self):
        res_dir = get_resource_dir()
        base_dir = get_base_dir()
        for candidate in [res_dir / "logo.ico", base_dir / "logo.ico", res_dir / "icon.ico", base_dir / "icon.ico"]:
            if candidate.exists():
                try:
                    self.root.iconbitmap(str(candidate))
                    break
                except Exception:
                    pass

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Yellow.Horizontal.TProgressbar",
            troughcolor="#1e293b",
            background=ACCENT_YELLOW,
            darkcolor=ACCENT_YELLOW,
            lightcolor=ACCENT_YELLOW,
            bordercolor="#1e293b",
            thickness=6
        )

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg=BG_DARK, padx=28, pady=16)
        header.pack(fill="x")

        # Top Badge
        badge_frame = tk.Frame(header, bg=BG_DARK)
        badge_frame.pack(anchor="w")

        badge = tk.Label(
            badge_frame,
            text="AUTONOMOUS AI VIDEO SUITE",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_YELLOW,
            bg=CARD_BG,
            padx=8,
            pady=2
        )
        badge.pack(side="left")

        # App Title (Crisp White + Accent Yellow)
        title_box = tk.Frame(header, bg=BG_DARK)
        title_box.pack(anchor="w", pady=(6, 2))

        title_white = tk.Label(
            title_box,
            text="OpenCut ",
            font=("Segoe UI", 20, "bold"),
            fg=TEXT_WHITE,
            bg=BG_DARK
        )
        title_white.pack(side="left")

        title_yellow = tk.Label(
            title_box,
            text="Enhanced",
            font=("Segoe UI", 20, "bold"),
            fg=ACCENT_YELLOW,
            bg=BG_DARK
        )
        title_yellow.pack(side="left")

        sub_lbl = tk.Label(
            header,
            text="1-Click Auto Clone, Setup & Extension Installer for Adobe Premiere Pro",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=BG_DARK
        )
        sub_lbl.pack(anchor="w")

        # 2. Main Minimal Card Container
        card = tk.Frame(self.root, bg=CARD_BG, padx=20, pady=14, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 12))

        # Installation Directory Selector
        dest_lbl = tk.Label(
            card,
            text="Install Destination Folder:",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg=CARD_BG
        )
        dest_lbl.pack(anchor="w", pady=(0, 4))

        dest_row = tk.Frame(card, bg=CARD_BG)
        dest_row.pack(fill="x", pady=(0, 10))

        self.path_entry = tk.Entry(
            dest_row,
            font=("Segoe UI", 9),
            bg=CARD_INNER,
            fg=TEXT_WHITE,
            insertbackground=TEXT_WHITE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.path_entry.insert(0, str(self.install_dir))
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        browse_btn = tk.Button(
            dest_row,
            text="Browse...",
            font=("Segoe UI", 8),
            bg=CARD_INNER,
            fg=TEXT_WHITE,
            activebackground=BORDER_COLOR,
            activeforeground=ACCENT_YELLOW,
            relief="flat",
            padx=10,
            cursor="hand2",
            command=self._on_browse
        )
        browse_btn.pack(side="right", ipady=2)

        # Features list
        features = [
            ("📥", "Auto-downloads & clones latest repository from GitHub"),
            ("⚡", "Configures Windows Registry for Premiere Pro (CSXS 9-18)"),
            ("🎬", "Installs OpenCut panel into Adobe CEP Extensions"),
            ("🖥️", "Creates 1-Click Desktop shortcut with official icon")
        ]

        for icon, text in features:
            row = tk.Frame(card, bg=CARD_BG)
            row.pack(fill="x", pady=2)
            ic_lbl = tk.Label(row, text=icon, font=("Segoe UI", 9), fg=ACCENT_YELLOW, bg=CARD_BG, width=3, anchor="w")
            ic_lbl.pack(side="left")
            tx_lbl = tk.Label(row, text=text, font=("Segoe UI", 8), fg=TEXT_WHITE, bg=CARD_BG, anchor="w")
            tx_lbl.pack(side="left")

        # Progress bar
        self.progress = ttk.Progressbar(card, style="Yellow.Horizontal.TProgressbar", mode="determinate", length=520)
        self.progress.pack(fill="x", pady=(12, 6))

        # Status text
        self.status_lbl = tk.Label(
            card,
            text="Ready to install. Click 'Install & Setup Now' to begin.",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.status_lbl.pack(fill="x")

        # 3. Action Buttons & GitHub Footer
        footer = tk.Frame(self.root, bg=BG_DARK, padx=28)
        footer.pack(fill="x")

        # Install Button
        self.install_btn = tk.Button(
            footer,
            text="Install & Setup Now",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_YELLOW,
            fg="#0f172a",
            activebackground=YELLOW_HOVER,
            activeforeground="#0f172a",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.start_installation
        )
        self.install_btn.pack(side="left")

        # GitHub Repo Link Button
        github_btn = tk.Button(
            footer,
            text="⭐ GitHub Repository",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_WHITE,
            activebackground="#1e293b",
            activeforeground=ACCENT_YELLOW,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.open_github
        )
        github_btn.pack(side="left", padx=(10, 0))

        # Exit / Cancel Button
        self.exit_btn = tk.Button(
            footer,
            text="Cancel",
            font=("Segoe UI", 9),
            bg=BG_DARK,
            fg=TEXT_MUTED,
            activebackground=CARD_BG,
            activeforeground=TEXT_WHITE,
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.root.quit
        )
        self.exit_btn.pack(side="right")

    def _on_browse(self):
        if self.is_installing:
            return
        selected = filedialog.askdirectory(
            initialdir=str(self.install_dir.parent if self.install_dir.parent.exists() else Path.home()),
            title="Select Destination Folder for OpenCut Enhanced"
        )
        if selected:
            self.install_dir = Path(selected) / "OpenCut-Enhanced" if not selected.endswith("OpenCut-Enhanced") else Path(selected)
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, str(self.install_dir))

    def open_github(self):
        webbrowser.open(GITHUB_REPO_URL)

    def update_status(self, text, progress_val, color=TEXT_WHITE):
        self.status_lbl.config(text=text, fg=color)
        self.progress["value"] = progress_val
        self.root.update_idletasks()

    def start_installation(self):
        if self.install_succeeded:
            self._launch_opencut_and_exit()
            return

        user_input = self.path_entry.get().strip()
        if user_input:
            self.install_dir = Path(user_input).resolve()

        self.is_installing = True
        self.install_btn.config(state="disabled", text="Installing...")
        self.path_entry.config(state="disabled")
        threading.Thread(target=self._run_install_thread, daemon=True).start()

    def _ensure_repository_downloaded(self, target_dir: Path):
        """Clones via git or downloads repository zip from GitHub and extracts it."""
        manifest = target_dir / "extension" / "com.opencut.panel" / "CSXS" / "manifest.xml"
        if manifest.exists():
            self.update_status("[1/5] Using verified OpenCut files in target directory...", 20)
            return

        target_dir.mkdir(parents=True, exist_ok=True)

        # Attempt 1: Git clone if git is installed
        git_bin = shutil.which("git")
        if git_bin:
            try:
                self.update_status("[1/5] Cloning repository via Git from GitHub...", 10)
                cmd = [git_bin, "clone", "--depth", "1", GITHUB_GIT_URL, str(target_dir)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and manifest.exists():
                    self.update_status("[1/5] Git clone completed successfully!", 25)
                    return
            except Exception:
                pass

        # Attempt 2: Direct HTTP zip download from GitHub
        self.update_status("[1/5] Downloading OpenCut suite from GitHub...", 10)
        temp_zip = target_dir.parent / "_opencut_main.zip"
        try:
            req = urllib.request.Request(GITHUB_ZIP_URL, headers={"User-Agent": "OpenCut-Enhanced-Installer/2.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(temp_zip, "wb") as f_out:
                content_len = resp.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len else 24 * 1024 * 1024
                downloaded = 0
                chunk_size = 65536
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    pct = 10 + int((downloaded / total_bytes) * 15)
                    mb = round(downloaded / (1024 * 1024), 1)
                    self.update_status(f"[1/5] Downloading suite: {mb} MB ({min(pct, 25)}%)...", min(pct, 25))

            self.update_status("[1/5] Unpacking repository files...", 25)
            with zipfile.ZipFile(temp_zip, "r") as zf:
                prefix = ""
                for member in zf.infolist():
                    if member.is_dir() and not prefix:
                        prefix = member.filename
                        break
                for member in zf.infolist():
                    rel_name = member.filename[len(prefix):] if prefix and member.filename.startswith(prefix) else member.filename
                    if not rel_name:
                        continue
                    dest_path = target_dir / rel_name
                    if member.is_dir():
                        dest_path.mkdir(parents=True, exist_ok=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except Exception:
                    pass
            self.update_status("[1/5] Repository files ready!", 30)
        except Exception as e:
            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Could not download repository from GitHub: {e}")

    def _run_install_thread(self):
        try:
            # 1. Ensure Repository is present (Clone or Download)
            self._ensure_repository_downloaded(self.install_dir)

            # 2. Windows Registry Configuration (PlayerDebugMode)
            self.update_status("[2/5] Configuring Windows Registry (PlayerDebugMode)...", 45)
            csxs_versions = [f"CSXS.{v}" for v in range(9, 19)]
            for ver in csxs_versions:
                cmd = f'reg add "HKEY_CURRENT_USER\\Software\\Adobe\\{ver}" /v PlayerDebugMode /t REG_SZ /d "1" /f'
                subprocess.run(cmd, shell=True, capture_output=True)

            # 3. Sync & Install CEP Extension to Adobe
            self.update_status("[3/5] Installing OpenCut panel into Premiere Pro...", 65)
            ws_ext = self.install_dir / "extension" / "com.opencut.panel"
            if ws_ext.exists():
                client_src = ws_ext / "client"
                client_dist = ws_ext / "client" / "dist"
                client_dist.mkdir(parents=True, exist_ok=True)
                for item in client_src.iterdir():
                    if item.name == "dist":
                        continue
                    if item.is_file():
                        shutil.copy2(item, client_dist / item.name)
                    elif item.is_dir() and item.name in ["locales", "assets"]:
                        shutil.copytree(item, client_dist / item.name, dirs_exist_ok=True)

                TARGET_EXT_DIR.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(ws_ext, TARGET_EXT_DIR, dirs_exist_ok=True)

            # 4. Create 1-Click Desktop Shortcut
            self.update_status("[4/5] Creating 1-Click Desktop Shortcut with official logo...", 80)
            desktop_path = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path.home() / "Desktop"

            shortcut_path = desktop_path / "OpenCut Enhanced.lnk"
            target_bat = (self.install_dir / "OpenCut-Launcher.vbs").resolve()
            if not target_bat.exists():
                target_bat = (self.install_dir / "Start-OpenCut.bat").resolve()
            icon_file = (self.install_dir / "logo.ico").resolve()
            if not icon_file.exists():
                icon_file = (self.install_dir / "icon.ico").resolve()

            # Clean existing shortcut to invalidate icon cache
            if shortcut_path.exists():
                try:
                    shortcut_path.unlink()
                except Exception:
                    pass

            vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{str(shortcut_path)}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{str(target_bat)}"
oLink.WorkingDirectory = "{str(self.install_dir.resolve())}"
oLink.Description = "OpenCut Enhanced - Autonomous AI Video Editor Studio"
oLink.IconLocation = "{str(icon_file)},0"
oLink.Save
"""
            tmp_vbs = self.install_dir / "_installer_tmp.vbs"
            with open(tmp_vbs, "w", encoding="utf-8") as f:
                f.write(vbs_script)
            subprocess.run(f'cscript //nologo "{tmp_vbs}"', shell=True, capture_output=True)
            if tmp_vbs.exists():
                os.remove(str(tmp_vbs))

            try:
                import ctypes
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
            except Exception:
                pass

            # 5. Environment & Python check
            self.update_status("[5/5] Checking Python & AI engine components...", 95)
            req_file = self.install_dir / "requirements.txt"
            py_bin = shutil.which("python") or (r"C:\Python313\python.exe" if Path(r"C:\Python313\python.exe").exists() else None)
            if py_bin and req_file.exists():
                try:
                    subprocess.run([py_bin, "-m", "pip", "install", "-r", str(req_file), "-q"], timeout=90, capture_output=True)
                except Exception:
                    pass

            # Completion
            self.install_succeeded = True
            self.is_installing = False
            self.update_status("✓ Installation complete! Ready to create in Premiere Pro.", 100, color=ACCENT_YELLOW)
            self.install_btn.config(
                state="normal",
                text="🚀 Launch OpenCut Studio",
                bg="#22c55e",
                fg=TEXT_WHITE
            )
            self.exit_btn.config(text="Close")

            messagebox.showinfo(
                "Installation Successful",
                f"🎉 OpenCut Enhanced has been installed successfully!\n\n"
                f"• Installed Location: {self.install_dir}\n"
                f"• Desktop Shortcut: 'OpenCut Enhanced' on Desktop\n"
                f"• Adobe Premiere Pro: Window -> Extensions -> OpenCut\n\n"
                f"Click 'Launch OpenCut Studio' to start the AI video engine."
            )
        except Exception as e:
            self.is_installing = False
            self.status_lbl.config(fg="#ef4444", text=f"Error: {e}")
            self.install_btn.config(state="normal", text="Retry Setup")
            messagebox.showerror("Installation Notice", str(e))

    def _launch_opencut_and_exit(self):
        launcher = (self.install_dir / "OpenCut-Launcher.vbs").resolve()
        if launcher.exists():
            try:
                subprocess.Popen(["wscript", str(launcher)], cwd=str(self.install_dir))
            except Exception:
                bat = (self.install_dir / "Start-OpenCut.bat").resolve()
                if bat.exists():
                    subprocess.Popen([str(bat)], cwd=str(self.install_dir), shell=True)
        self.root.quit()

def main():
    root = tk.Tk()
    app = OpenCutMinimalInstaller(root)
    root.mainloop()

if __name__ == "__main__":
    main()
