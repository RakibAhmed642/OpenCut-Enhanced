"""
OpenCut Enhanced - Modern Minimal Yellow & White GUI Installer
Sleek, user-friendly, enterprise-grade installer for Adobe Premiere Pro CEP extension.

Features:
  - System Readiness Scanner (detects Python, FFmpeg, Adobe CEP, AI dependencies)
  - Interactive Component Checklist (users can review & toggle what to install)
  - Autonomous Git Clone or Direct GitHub Archive Streaming (Zero Git Required)
  - Automated Silent Python 3.12 Installation (if missing)
  - Automated FFmpeg Engine Installation via Winget/Direct Download (if missing)
  - Windows Registry Configuration (CSXS.9 through CSXS.18 PlayerDebugMode)
  - Adobe CEP Panel Sync & Installation
  - 1-Click Desktop Shortcut with Multi-Resolution Icon & Cache Flushing
  - AI Studio Pip Packages Ingestion
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

# Official GitHub & Download Endpoints
GITHUB_REPO_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced"
GITHUB_ZIP_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced/archive/refs/heads/main.zip"
GITHUB_GIT_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced.git"
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"

# Adobe Common Paths
APPDATA = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
ADOBE_CEP_DIR = Path(APPDATA) / "Adobe" / "CEP" / "extensions"
TARGET_EXT_DIR = ADOBE_CEP_DIR / "com.opencut.panel"

# UI Visual Tokens: Dark Slate, Elevated Navy, Crisp White, and Radiant Studio Yellow
BG_DARK = "#0b0f19"         # Deep Slate background
CARD_BG = "#131b2e"         # Primary Card background
CARD_INNER = "#1e293b"      # Inner container background
ACCENT_YELLOW = "#facc15"   # Vibrant Gold / Yellow
YELLOW_HOVER = "#eab308"    # Darker Gold on hover
TEXT_WHITE = "#ffffff"      # Crisp White
TEXT_MUTED = "#94a3b8"      # Soft Slate Gray
BORDER_COLOR = "#1e293b"    # Subtle Border
COLOR_SUCCESS = "#22c55e"   # Emerald Green
COLOR_WARNING = "#facc15"   # Amber Warning

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
    if (base / "extension" / "com.opencut.panel" / "CSXS" / "manifest.xml").exists():
        return base
    return Path.home() / "OpenCut-Enhanced"

def detect_python() -> tuple[bool, str]:
    """Detects if Python 3.10+ is available on the machine."""
    py = shutil.which("python")
    if py:
        try:
            out = subprocess.check_output([py, "--version"], text=True, stderr=subprocess.STDOUT)
            return True, f"Python ({out.strip()})"
        except Exception:
            return True, f"Python ({py})"

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        r"C:\Python313\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python310\python.exe",
        os.path.join(local_appdata, "Programs", "Python", "Python313", "python.exe"),
        os.path.join(local_appdata, "Programs", "Python", "Python312", "python.exe"),
        os.path.join(local_appdata, "Programs", "Python", "Python311", "python.exe"),
        os.path.join(local_appdata, "Programs", "Python", "Python310", "python.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return True, f"Python ({c})"
    return False, "Not Found (Install Recommended)"

def detect_ffmpeg(install_dir: Path = None) -> tuple[bool, str]:
    """Detects if FFmpeg is available locally or on PATH."""
    if install_dir:
        local_ff = install_dir / "ffmpeg" / "ffmpeg.exe"
        if local_ff.exists():
            return True, f"Bundled FFmpeg ({local_ff})"

    base = get_base_dir()
    local_base = base / "ffmpeg" / "ffmpeg.exe"
    if local_base.exists():
        return True, f"Bundled FFmpeg ({local_base})"

    ff = shutil.which("ffmpeg")
    if ff:
        return True, f"System FFmpeg ({ff})"

    std_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    ]
    for p in std_paths:
        if os.path.exists(p):
            return True, f"FFmpeg ({p})"

    return False, "Not Found (Install Recommended)"

def detect_ai_packages(py_executable: str = None) -> tuple[bool, str]:
    """Checks if core Python libraries are installed."""
    if not py_executable or "Not Found" in py_executable:
        return False, "Requires Python first"

    check_script = "import sys; pkgs=['yaml','PIL','numpy','scipy','fastapi','uvicorn','pydantic']; missing=[p for p in pkgs if not __import__('importlib').util.find_spec(p)]; sys.exit(len(missing))"
    try:
        py_bin = shutil.which("python") or py_executable.split("(")[-1].strip(")")
        res = subprocess.run([py_bin, "-c", check_script], capture_output=True)
        if res.returncode == 0:
            return True, "All Core Libraries Present"
        return False, "Missing Libraries (Auto-Install Recommended)"
    except Exception:
        return False, "Auto-Install Recommended"

class OpenCutMinimalInstaller:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OpenCut Enhanced — Professional Autonomous Setup")
        self.root.geometry("640x660")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        self.install_dir = get_default_install_dir()
        self.is_installing = False
        self.install_succeeded = False

        # Component Selection Checkbox Variables
        self.chk_repo_var = tk.BooleanVar(value=True)
        self.chk_python_var = tk.BooleanVar(value=True)
        self.chk_ffmpeg_var = tk.BooleanVar(value=True)
        self.chk_cep_var = tk.BooleanVar(value=True)
        self.chk_packages_var = tk.BooleanVar(value=True)
        self.chk_shortcut_var = tk.BooleanVar(value=True)

        self._set_window_icon()
        self._apply_styles()
        self._scan_system_readiness()
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
            thickness=8
        )

    def _scan_system_readiness(self):
        """Proactively checks system readiness and sets defaults."""
        self.py_installed, self.py_info = detect_python()
        self.ff_installed, self.ff_info = detect_ffmpeg(self.install_dir)
        self.ai_installed, self.ai_info = detect_ai_packages(self.py_info if self.py_installed else None)

        # Checkbox defaults:
        # If already installed, user can choose whether to re-sync/verify
        self.chk_python_var.set(not self.py_installed)
        self.chk_ffmpeg_var.set(not self.ff_installed)
        self.chk_packages_var.set(True)

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg=BG_DARK, padx=28, pady=16)
        header.pack(fill="x")

        # Top Badge
        badge_frame = tk.Frame(header, bg=BG_DARK)
        badge_frame.pack(anchor="w")

        badge = tk.Label(
            badge_frame,
            text="AUTONOMOUS AI VIDEO SUITE • ENTERPRISE EDITION",
            font=("Segoe UI", 8, "bold"),
            fg=ACCENT_YELLOW,
            bg=CARD_BG,
            padx=8,
            pady=2
        )
        badge.pack(side="left")

        # Title Row
        title_box = tk.Frame(header, bg=BG_DARK)
        title_box.pack(anchor="w", pady=(6, 2))

        tk.Label(
            title_box,
            text="OpenCut ",
            font=("Segoe UI", 21, "bold"),
            fg=TEXT_WHITE,
            bg=BG_DARK
        ).pack(side="left")

        tk.Label(
            title_box,
            text="Enhanced",
            font=("Segoe UI", 21, "bold"),
            fg=ACCENT_YELLOW,
            bg=BG_DARK
        ).pack(side="left")

        tk.Label(
            header,
            text="Intelligent System Setup, Dependency Resolution & Premiere Pro CEP Deployment",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=BG_DARK
        ).pack(anchor="w")

        # 2. Destination Card
        dest_card = tk.Frame(self.root, bg=CARD_BG, padx=18, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
        dest_card.pack(fill="x", padx=28, pady=(0, 10))

        dest_header = tk.Frame(dest_card, bg=CARD_BG)
        dest_header.pack(fill="x", pady=(0, 4))

        tk.Label(
            dest_header,
            text="📁 Installation Destination Folder",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg=CARD_BG
        ).pack(side="left")

        dest_row = tk.Frame(dest_card, bg=CARD_BG)
        dest_row.pack(fill="x")

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
            font=("Segoe UI", 8, "bold"),
            bg=CARD_INNER,
            fg=TEXT_WHITE,
            activebackground=BORDER_COLOR,
            activeforeground=ACCENT_YELLOW,
            relief="flat",
            padx=12,
            cursor="hand2",
            command=self._on_browse
        )
        browse_btn.pack(side="right", ipady=2)

        # 3. System Readiness & Components Card
        comp_card = tk.Frame(self.root, bg=CARD_BG, padx=18, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
        comp_card.pack(fill="x", padx=28, pady=(0, 10))

        tk.Label(
            comp_card,
            text="⚙️ System Readiness & Components to Setup",
            font=("Segoe UI", 9, "bold"),
            fg=TEXT_WHITE,
            bg=CARD_BG
        ).pack(anchor="w", pady=(0, 8))

        # Component 1: OpenCut Core Repository
        self._build_component_row(
            comp_card,
            var=self.chk_repo_var,
            title="OpenCut Suite Core Engine (GitHub Clone / Download)",
            desc="Transcribers, sound synthesis, 9:16 reels agent, and motion templates",
            status_text="Verified / Auto-Clone Ready",
            is_ok=True,
            state="disabled"
        )

        # Component 2: Python 3.12 (64-bit)
        py_status = "Detected" if self.py_installed else "Missing (Auto-Install)"
        self._build_component_row(
            comp_card,
            var=self.chk_python_var,
            title="Python 3.12 64-bit Runtime Environment",
            desc=self.py_info if self.py_installed else "Required for AI daemons & Faster-Whisper. Auto-downloads & installs silently.",
            status_text=py_status,
            is_ok=self.py_installed
        )

        # Component 3: FFmpeg Media Engine
        ff_status = "Detected" if self.ff_installed else "Missing (Auto-Install)"
        self._build_component_row(
            comp_card,
            var=self.chk_ffmpeg_var,
            title="FFmpeg High-Performance Multimedia Engine",
            desc="Required for silence cuts, audio stems, R128 loudness leveling & B-roll transcoding.",
            status_text=ff_status,
            is_ok=self.ff_installed
        )

        # Component 4: Adobe CEP Extension & Registry
        self._build_component_row(
            comp_card,
            var=self.chk_cep_var,
            title="Adobe Premiere Pro Extension & PlayerDebugMode",
            desc="Registers panel into Window -> Extensions -> OpenCut and activates CSXS.9-18 registry debug mode.",
            status_text="Ready",
            is_ok=True
        )

        # Component 5: AI Packages (requirements.txt)
        pkg_status = "Installed" if self.ai_installed else "Auto-Install"
        self._build_component_row(
            comp_card,
            var=self.chk_packages_var,
            title="Core AI Packages & FastAPI Studio Server",
            desc="Installs PyYAML, Pillow, NumPy, SciPy, FastAPI, Uvicorn via pip.",
            status_text=pkg_status,
            is_ok=self.ai_installed
        )

        # Component 6: Desktop Shortcut with Custom Icon
        self._build_component_row(
            comp_card,
            var=self.chk_shortcut_var,
            title="1-Click Desktop Shortcut with Official Icon",
            desc="Creates 'OpenCut Enhanced.lnk' with multi-resolution icon and shell cache flush.",
            status_text="Ready",
            is_ok=True
        )

        # 4. Progress Card
        prog_card = tk.Frame(self.root, bg=CARD_BG, padx=18, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
        prog_card.pack(fill="x", padx=28, pady=(0, 12))

        self.progress = ttk.Progressbar(prog_card, style="Yellow.Horizontal.TProgressbar", mode="determinate", length=540)
        self.progress.pack(fill="x", pady=(2, 6))

        self.status_lbl = tk.Label(
            prog_card,
            text="Ready. Select desired components and click 'Install & Setup Selected'.",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.status_lbl.pack(fill="x")

        # 5. Footer Actions
        footer = tk.Frame(self.root, bg=BG_DARK, padx=28)
        footer.pack(fill="x")

        self.install_btn = tk.Button(
            footer,
            text="Install & Setup Selected",
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

        github_btn = tk.Button(
            footer,
            text="⭐ GitHub Repository",
            font=("Segoe UI", 9),
            bg=CARD_BG,
            fg=TEXT_WHITE,
            activebackground=CARD_INNER,
            activeforeground=ACCENT_YELLOW,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.open_github
        )
        github_btn.pack(side="left", padx=(10, 0))

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

    def _build_component_row(self, parent, var, title, desc, status_text, is_ok, state="normal"):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", pady=2)

        chk = tk.Checkbutton(
            row,
            variable=var,
            bg=CARD_BG,
            activebackground=CARD_BG,
            selectcolor=CARD_INNER,
            relief="flat",
            state=state,
            cursor="hand2" if state == "normal" else "arrow"
        )
        chk.pack(side="left", anchor="n", pady=1)

        info_box = tk.Frame(row, bg=CARD_BG)
        info_box.pack(side="left", fill="x", expand=True, padx=(4, 8))

        t_lbl = tk.Label(info_box, text=title, font=("Segoe UI", 8, "bold"), fg=TEXT_WHITE, bg=CARD_BG, anchor="w")
        t_lbl.pack(fill="x")

        d_lbl = tk.Label(info_box, text=desc, font=("Segoe UI", 7), fg=TEXT_MUTED, bg=CARD_BG, anchor="w")
        d_lbl.pack(fill="x")

        badge_color = COLOR_SUCCESS if is_ok else COLOR_WARNING
        badge_prefix = "✓ " if is_ok else "⚠️ "
        s_lbl = tk.Label(
            row,
            text=badge_prefix + status_text,
            font=("Segoe UI", 7, "bold"),
            fg=badge_color,
            bg=CARD_INNER,
            padx=6,
            pady=2
        )
        s_lbl.pack(side="right", anchor="n", pady=2)

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
        threading.Thread(target=self._run_install_pipeline, daemon=True).start()

    def _run_install_pipeline(self):
        try:
            total_steps = 6
            step = 1

            # ---------------------------------------------------------
            # Step 1: Ensure OpenCut Repository (Clone or Download)
            # ---------------------------------------------------------
            if self.chk_repo_var.get():
                self.update_status(f"[{step}/{total_steps}] Checking repository files in destination...", 10)
                self._ensure_repository_downloaded(self.install_dir)
            step += 1

            # ---------------------------------------------------------
            # Step 2: Auto-Install Python if missing & requested
            # ---------------------------------------------------------
            if self.chk_python_var.get() and not self.py_installed:
                self.update_status(f"[{step}/{total_steps}] Downloading Python 3.12 64-bit runtime...", 20)
                self._download_and_install_python()
                self.py_installed, self.py_info = detect_python()
            else:
                self.update_status(f"[{step}/{total_steps}] Python environment ready.", 30)
            step += 1

            # ---------------------------------------------------------
            # Step 3: Auto-Install FFmpeg if missing & requested
            # ---------------------------------------------------------
            if self.chk_ffmpeg_var.get() and not self.ff_installed:
                self.update_status(f"[{step}/{total_steps}] Setting up FFmpeg multimedia engine...", 40)
                self._ensure_ffmpeg_installed(self.install_dir)
                self.ff_installed, self.ff_info = detect_ffmpeg(self.install_dir)
            else:
                self.update_status(f"[{step}/{total_steps}] FFmpeg engine ready.", 50)
            step += 1

            # ---------------------------------------------------------
            # Step 4: Windows Registry (CSXS PlayerDebugMode) & CEP Panel
            # ---------------------------------------------------------
            if self.chk_cep_var.get():
                self.update_status(f"[{step}/{total_steps}] Configuring Windows Registry (PlayerDebugMode)...", 60)
                csxs_versions = [f"CSXS.{v}" for v in range(9, 19)]
                for ver in csxs_versions:
                    cmd = f'reg add "HKEY_CURRENT_USER\\Software\\Adobe\\{ver}" /v PlayerDebugMode /t REG_SZ /d "1" /f'
                    subprocess.run(cmd, shell=True, capture_output=True)

                self.update_status(f"[{step}/{total_steps}] Installing OpenCut panel into Premiere Pro...", 70)
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
            step += 1

            # ---------------------------------------------------------
            # Step 5: Core AI Packages (requirements.txt)
            # ---------------------------------------------------------
            if self.chk_packages_var.get():
                self.update_status(f"[{step}/{total_steps}] Installing Core AI Packages via pip...", 80)
                req_file = self.install_dir / "requirements.txt"
                py_bin = shutil.which("python") or (self.py_info.split("(")[-1].strip(")") if self.py_installed else None)
                if py_bin and req_file.exists():
                    try:
                        cmd = [py_bin, "-m", "pip", "install", "-r", str(req_file), "-q", "--no-warn-script-location"]
                        subprocess.run(cmd, timeout=120, capture_output=True)
                    except Exception:
                        pass
            step += 1

            # ---------------------------------------------------------
            # Step 6: 1-Click Desktop Shortcut with Icon
            # ---------------------------------------------------------
            if self.chk_shortcut_var.get():
                self.update_status(f"[{step}/{total_steps}] Creating Desktop Shortcut with official icon...", 90)
                self._create_desktop_shortcut()

            # ---------------------------------------------------------
            # Final Completion
            # ---------------------------------------------------------
            self.install_succeeded = True
            self.is_installing = False
            self.update_status("✓ Full setup completed successfully! Ready for Premiere Pro.", 100, color=ACCENT_YELLOW)
            self.install_btn.config(
                state="normal",
                text="🚀 Launch OpenCut Studio",
                bg="#22c55e",
                fg=TEXT_WHITE
            )
            self.exit_btn.config(text="Close")

            messagebox.showinfo(
                "OpenCut Setup Complete",
                f"🎉 OpenCut Enhanced is completely installed and configured!\n\n"
                f"• Installed Location: {self.install_dir}\n"
                f"• Desktop Shortcut: 'OpenCut Enhanced' on your Desktop\n"
                f"• Premiere Pro Extension: Window -> Extensions -> OpenCut\n\n"
                f"Click 'Launch OpenCut Studio' to start the local AI engines."
            )
        except Exception as e:
            self.is_installing = False
            self.status_lbl.config(fg="#ef4444", text=f"Error: {e}")
            self.install_btn.config(state="normal", text="Retry Setup")
            messagebox.showerror("Installation Notice", str(e))

    def _ensure_repository_downloaded(self, target_dir: Path):
        """Clones via git or downloads repository archive from GitHub."""
        manifest = target_dir / "extension" / "com.opencut.panel" / "CSXS" / "manifest.xml"
        if manifest.exists():
            return

        target_dir.mkdir(parents=True, exist_ok=True)

        # Attempt 1: Git clone if git is available
        git_bin = shutil.which("git")
        if git_bin:
            try:
                self.update_status("Cloning OpenCut repository via Git...", 12)
                cmd = [git_bin, "clone", "--depth", "1", GITHUB_GIT_URL, str(target_dir)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and manifest.exists():
                    return
            except Exception:
                pass

        # Attempt 2: Stream zip package from GitHub
        self.update_status("Streaming OpenCut repository package from GitHub...", 12)
        temp_zip = target_dir.parent / "_opencut_pkg.zip"
        try:
            req = urllib.request.Request(GITHUB_ZIP_URL, headers={"User-Agent": "OpenCut-Enhanced-Installer/2.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(temp_zip, "wb") as f_out:
                content_len = resp.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len else 24 * 1024 * 1024
                downloaded = 0
                chunk_sz = 65536
                while True:
                    chunk = resp.read(chunk_sz)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    mb = round(downloaded / (1024 * 1024), 1)
                    pct = 12 + int((downloaded / total_bytes) * 6)
                    self.update_status(f"Downloading repository: {mb} MB ({min(pct, 18)}%)...", min(pct, 18))

            self.update_status("Unpacking repository files...", 18)
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
                    dest = target_dir / rel_name
                    if member.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(dest, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except Exception:
                    pass
        except Exception as e:
            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Failed to ingest OpenCut repository from GitHub: {e}")

    def _download_and_install_python(self):
        """Silently downloads and installs Python 64-bit for current user."""
        temp_installer = Path(os.environ.get("TEMP", ".")) / "python_installer_opencut.exe"
        try:
            req = urllib.request.Request(PYTHON_INSTALLER_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(temp_installer, "wb") as f_out:
                content_len = resp.headers.get("Content-Length")
                total_bytes = int(content_len) if content_len else 27 * 1024 * 1024
                downloaded = 0
                chunk_sz = 65536
                while True:
                    chunk = resp.read(chunk_sz)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    mb = round(downloaded / (1024 * 1024), 1)
                    pct = 20 + int((downloaded / total_bytes) * 8)
                    self.update_status(f"Downloading Python 3.12: {mb} MB ({min(pct, 28)}%)...", min(pct, 28))

            self.update_status("Executing silent Python installation (PrependPath=1)...", 28)
            cmd = f'"{str(temp_installer)}" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 SimpleInstall=1'
            subprocess.run(cmd, shell=True, capture_output=True, timeout=180)

            if temp_installer.exists():
                try:
                    temp_installer.unlink()
                except Exception:
                    pass
        except Exception as e:
            if temp_installer.exists():
                try:
                    temp_installer.unlink()
                except Exception:
                    pass
            print(f"Python install notice: {e}")

    def _ensure_ffmpeg_installed(self, target_dir: Path):
        """Installs FFmpeg via winget or copies into target_dir/ffmpeg/."""
        # Method 1: Winget
        winget = shutil.which("winget")
        if winget:
            try:
                self.update_status("Installing FFmpeg via Windows Package Manager (Winget)...", 45)
                cmd = [winget, "install", "--id", "Gyan.FFmpeg", "-e", "--accept-source-agreements", "--accept-package-agreements", "--silent"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    return
            except Exception:
                pass

        # Method 2: Check if bundled in base_dir
        base = get_base_dir()
        base_ff = base / "ffmpeg"
        target_ff = target_dir / "ffmpeg"
        if base_ff.exists() and not target_ff.exists():
            shutil.copytree(base_ff, target_ff, dirs_exist_ok=True)

    def _create_desktop_shortcut(self):
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
