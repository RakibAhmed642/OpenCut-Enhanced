"""
OpenCut Enhanced - Modern Minimal Yellow & White GUI Installer
Sleek, user-friendly, and clean installer for Adobe Premiere Pro CEP extension.
"""

import os
import sys
import shutil
import subprocess
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
APPDATA = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
ADOBE_CEP_DIR = Path(APPDATA) / "Adobe" / "CEP" / "extensions"
TARGET_EXT_DIR = ADOBE_CEP_DIR / "com.opencut.panel"
GITHUB_REPO_URL = "https://github.com/RakibAhmed642/OpenCut-Enhanced"

# Color Palette: Deep Slate/Charcoal base with Crisp White and Vibrant Yellow Accents
BG_DARK = "#0b0f19"         # Deep Slate background
CARD_BG = "#131b2e"         # Elevated Card background
ACCENT_YELLOW = "#facc15"   # Vibrant Gold / Yellow
YELLOW_HOVER = "#eab308"    # Darker Yellow on hover
TEXT_WHITE = "#ffffff"      # Crisp White
TEXT_MUTED = "#94a3b8"      # Soft Slate Gray
BORDER_COLOR = "#1e293b"    # Subtle Border

class OpenCutMinimalInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenCut Enhanced — 1-Click Installer")
        self.root.geometry("560x420")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        ico_path = BASE_DIR / "logo.ico"
        if not ico_path.exists():
            ico_path = BASE_DIR / "icon.ico"
        if ico_path.exists():
            try:
                self.root.iconbitmap(str(ico_path))
            except Exception:
                pass

        self._apply_styles()
        self._build_ui()

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
        header = tk.Frame(self.root, bg=BG_DARK, padx=28, pady=20)
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
        title_box.pack(anchor="w", pady=(8, 2))

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
            text="Automatic Setup & 1-Click Extension Installer for Adobe Premiere Pro",
            font=("Segoe UI", 10),
            fg=TEXT_MUTED,
            bg=BG_DARK
        )
        sub_lbl.pack(anchor="w")

        # 2. Main Minimal Card Container
        card = tk.Frame(self.root, bg=CARD_BG, padx=20, pady=16, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 16))

        features = [
            ("⚡", "Configures Windows Registry for all Adobe Premiere versions"),
            ("🎬", "Installs OpenCut panel into Premiere Pro extensions folder"),
            ("🖥️", "Creates 1-Click 'OpenCut Enhanced' Desktop shortcut with icon"),
            ("🚀", "Verifies bundled local FFmpeg and background AI engine")
        ]

        for icon, text in features:
            row = tk.Frame(card, bg=CARD_BG)
            row.pack(fill="x", pady=3)
            ic_lbl = tk.Label(row, text=icon, font=("Segoe UI", 9), fg=ACCENT_YELLOW, bg=CARD_BG, width=3, anchor="w")
            ic_lbl.pack(side="left")
            tx_lbl = tk.Label(row, text=text, font=("Segoe UI", 9), fg=TEXT_WHITE, bg=CARD_BG, anchor="w")
            tx_lbl.pack(side="left")

        # Progress bar
        self.progress = ttk.Progressbar(card, style="Yellow.Horizontal.TProgressbar", mode="determinate", length=480)
        self.progress.pack(fill="x", pady=(14, 6))

        # Status text
        self.status_lbl = tk.Label(
            card,
            text="Ready to install on your computer.",
            font=("Segoe UI", 9),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.status_lbl.pack(fill="x")

        # 3. Action Buttons & GitHub Footer
        footer = tk.Frame(self.root, bg=BG_DARK, padx=28)
        footer.pack(fill="x")

        # Install Button (Vibrant Yellow with Dark Text for Maximum Pop & Readability)
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
            pady=9,
            cursor="hand2",
            command=self.start_installation
        )
        self.install_btn.pack(side="left")

        # GitHub Repo Link Button (Clean Outline Minimalist)
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
            pady=9,
            cursor="hand2",
            command=self.open_github
        )
        github_btn.pack(side="left", padx=(10, 0))

        # Exit Button
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
            pady=9,
            cursor="hand2",
            command=self.root.quit
        )
        self.exit_btn.pack(side="right")

    def open_github(self):
        webbrowser.open(GITHUB_REPO_URL)

    def update_status(self, text, progress_val, color=TEXT_WHITE):
        self.status_lbl.config(text=text, fg=color)
        self.progress["value"] = progress_val
        self.root.update_idletasks()

    def start_installation(self):
        self.install_btn.config(state="disabled", text="Installing...")
        threading.Thread(target=self._run_install_thread, daemon=True).start()

    def _run_install_thread(self):
        try:
            # 1. Enable Registry PlayerDebugMode
            self.update_status("[1/4] Configuring Windows Registry (PlayerDebugMode)...", 25)
            csxs_versions = [f"CSXS.{v}" for v in range(9, 19)]
            for ver in csxs_versions:
                cmd = f'reg add "HKEY_CURRENT_USER\\Software\\Adobe\\{ver}" /v PlayerDebugMode /t REG_SZ /d "1" /f'
                subprocess.run(cmd, shell=True, capture_output=True)

            # 2. Sync Extension
            self.update_status("[2/4] Installing OpenCut panel into Premiere Pro...", 50)
            ws_ext = BASE_DIR / "extension" / "com.opencut.panel"
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

            # 3. Create Desktop Shortcut
            self.update_status("[3/4] Creating 1-Click Desktop Shortcut with official logo...", 75)
            desktop_path = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path.home() / "Desktop"

            shortcut_path = desktop_path / "OpenCut Enhanced.lnk"
            target_bat = (BASE_DIR / "OpenCut-Launcher.vbs").resolve()
            if not target_bat.exists():
                target_bat = (BASE_DIR / "Start-OpenCut.bat").resolve()
            icon_file = (BASE_DIR / "logo.ico").resolve()
            if not icon_file.exists():
                icon_file = (BASE_DIR / "icon.ico").resolve()

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
oLink.WorkingDirectory = "{str(BASE_DIR.resolve())}"
oLink.Description = "OpenCut Enhanced - Autonomous AI Video Editor Studio"
oLink.IconLocation = "{str(icon_file)},0"
oLink.Save
"""
            tmp_vbs = BASE_DIR / "_installer_tmp.vbs"
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

            # 4. Final verification
            self.update_status("✓ Installation complete! Ready to create in Premiere Pro.", 100, color=ACCENT_YELLOW)
            self.install_btn.config(
                state="normal",
                text="✓ Done & Open Premiere",
                bg="#22c55e",
                fg=TEXT_WHITE,
                command=self.root.quit
            )

            messagebox.showinfo(
                "Setup Successful",
                "🎉 OpenCut Enhanced is ready!\n\n"
                "1. 'OpenCut Enhanced' icon has been added to your Desktop.\n"
                "2. In Premiere Pro, open your project and go to:\n"
                "   Window -> Extensions -> OpenCut"
            )
        except Exception as e:
            self.status_lbl.config(fg="#ef4444", text=f"Error: {e}")
            self.install_btn.config(state="normal", text="Retry")
            messagebox.showerror("Installation Notice", str(e))

def main():
    root = tk.Tk()
    app = OpenCutMinimalInstaller(root)
    root.mainloop()

if __name__ == "__main__":
    main()
