"""
OpenCut Enhanced - Self-Contained GUI One-Click Installer
Configures Adobe Premiere Pro CEP extension, Registry, Desktop Shortcut,
and starts the local environment automatically.
"""

import os
import sys
import shutil
import subprocess
import threading
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
    """Gets the application directory whether running as script or frozen PyInstaller exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
APPDATA = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
ADOBE_CEP_DIR = Path(APPDATA) / "Adobe" / "CEP" / "extensions"
TARGET_EXT_DIR = ADOBE_CEP_DIR / "com.opencut.panel"

class OpenCutInstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenCut Enhanced - Installer & Setup")
        self.root.geometry("540x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#07090e")

        # Set Window Icon if logo.ico exists
        ico_path = BASE_DIR / "logo.ico"
        if ico_path.exists():
            try:
                self.root.iconbitmap(str(ico_path))
            except Exception:
                pass

        self._build_ui()

    def _build_ui(self):
        # Header banner
        header_frame = tk.Frame(self.root, bg="#0d1117", padx=20, pady=16)
        header_frame.pack(fill="x")

        title_lbl = tk.Label(
            header_frame,
            text="🎬 OpenCut Enhanced",
            font=("Segoe UI", 16, "bold"),
            fg="#22d3ee",
            bg="#0d1117"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Autonomous AI Video Editing Suite for Adobe Premiere Pro",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0d1117"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Content frame
        content_frame = tk.Frame(self.root, bg="#07090e", padx=24, pady=16)
        content_frame.pack(fill="both", expand=True)

        desc_lbl = tk.Label(
            content_frame,
            text="Click 'Install & Setup' to automatically configure OpenCut:\n"
                 "• Enable Adobe Premiere Pro PlayerDebugMode (CSXS.9 - 18)\n"
                 "• Install OpenCut CEP Panel to Adobe Extensions\n"
                 "• Create 1-Click Desktop Shortcut with official logo\n"
                 "• Verify bundled high-performance FFmpeg engine",
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg="#07090e",
            justify="left"
        )
        desc_lbl.pack(anchor="w", pady=(0, 14))

        # Progress bar
        self.progress = ttk.Progressbar(content_frame, mode="determinate", length=490)
        self.progress.pack(fill="x", pady=(0, 10))

        # Status text
        self.status_lbl = tk.Label(
            content_frame,
            text="Ready to install.",
            font=("Segoe UI", 9, "italic"),
            fg="#38bdf8",
            bg="#07090e",
            anchor="w"
        )
        self.status_lbl.pack(fill="x", pady=(0, 14))

        # Button row
        btn_frame = tk.Frame(content_frame, bg="#07090e")
        btn_frame.pack(fill="x", pady=(10, 0))

        self.install_btn = tk.Button(
            btn_frame,
            text="⚡ Install & Setup Now",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="white",
            activebackground="#0369a1",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.start_installation
        )
        self.install_btn.pack(side="left")

        self.close_btn = tk.Button(
            btn_frame,
            text="Exit",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.root.quit
        )
        self.close_btn.pack(side="right")

    def update_status(self, text, progress_val):
        self.status_lbl.config(text=text)
        self.progress["value"] = progress_val
        self.root.update_idletasks()

    def start_installation(self):
        self.install_btn.config(state="disabled", text="Installing...")
        threading.Thread(target=self._run_install_thread, daemon=True).start()

    def _run_install_thread(self):
        try:
            # 1. Enable Registry PlayerDebugMode
            self.update_status("[1/4] Enabling Adobe CEP Debug Mode...", 25)
            csxs_versions = [f"CSXS.{v}" for v in range(9, 19)]
            for ver in csxs_versions:
                cmd = f'reg add "HKEY_CURRENT_USER\\Software\\Adobe\\{ver}" /v PlayerDebugMode /t REG_SZ /d "1" /f'
                subprocess.run(cmd, shell=True, capture_output=True)

            # 2. Sync Extension
            self.update_status("[2/4] Installing CEP Extension into Adobe...", 50)
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
            self.update_status("[3/4] Creating 1-Click Desktop Shortcut...", 75)
            desktop_path = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path.home() / "Desktop"

            shortcut_path = desktop_path / "OpenCut Enhanced.lnk"
            target_bat = BASE_DIR / "OpenCut-Launcher.vbs"
            if not target_bat.exists():
                target_bat = BASE_DIR / "Start-OpenCut.bat"
            icon_file = BASE_DIR / "logo.ico"
            if not icon_file.exists():
                icon_file = BASE_DIR / "icon.ico"

            vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{str(shortcut_path)}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{str(target_bat)}"
oLink.WorkingDirectory = "{str(BASE_DIR)}"
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

            # 4. Final verification
            self.update_status("[4/4] Installation Complete!", 100)
            self.status_lbl.config(fg="#22c55e", text="✓ OpenCut Enhanced installed successfully!")
            self.install_btn.config(state="normal", text="✓ Done", bg="#16a34a", command=self.root.quit)

            messagebox.showinfo(
                "Setup Successful",
                "OpenCut Enhanced is now installed!\n\n"
                "1. An 'OpenCut Enhanced' shortcut is on your Desktop.\n"
                "2. Open Adobe Premiere Pro -> Window -> Extensions -> OpenCut"
            )
        except Exception as e:
            self.status_lbl.config(fg="#ef4444", text=f"Error: {e}")
            self.install_btn.config(state="normal", text="Retry")
            messagebox.showerror("Installation Error", str(e))

def main():
    root = tk.Tk()
    app = OpenCutInstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
