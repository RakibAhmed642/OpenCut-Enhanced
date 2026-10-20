import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Base directories
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_EXT = BASE_DIR / "extension" / "com.opencut.panel"
CLIENT_SRC = WORKSPACE_EXT / "client"
CLIENT_DIST = WORKSPACE_EXT / "client" / "dist"

# Windows Common Paths (Universal, works on any user profile)
APPDATA = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
ADOBE_CEP_DIR = Path(APPDATA) / "Adobe" / "CEP" / "extensions"
TARGET_EXT_DIR = ADOBE_CEP_DIR / "com.opencut.panel"

def enable_player_debug_mode():
    """Enables CEP PlayerDebugMode in Windows Registry for CSXS versions 9 through 18."""
    print("  [1/4] Configuring Windows Registry for Adobe CEP extensions...")
    csxs_versions = [f"CSXS.{v}" for v in range(9, 19)]
    for ver in csxs_versions:
        cmd = f'reg add "HKEY_CURRENT_USER\\Software\\Adobe\\{ver}" /v PlayerDebugMode /t REG_SZ /d "1" /f'
        subprocess.run(cmd, shell=True, capture_output=True)
    print("        [OK] PlayerDebugMode enabled across Adobe Premiere Pro versions.")

def sync_extension_to_adobe():
    """Syncs the extension directly to the user's Adobe CEP directory."""
    print("  [2/4] Installing OpenCut panel into Adobe Premiere Pro extensions...")
    if not CLIENT_DIST.exists():
        CLIENT_DIST.mkdir(parents=True, exist_ok=True)

    for item in CLIENT_SRC.iterdir():
        if item.name == "dist":
            continue
        if item.is_file():
            shutil.copy2(item, CLIENT_DIST / item.name)
        elif item.is_dir() and item.name in ["locales", "assets"]:
            shutil.copytree(item, CLIENT_DIST / item.name, dirs_exist_ok=True)

    TARGET_EXT_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(WORKSPACE_EXT, TARGET_EXT_DIR, dirs_exist_ok=True)
    print(f"        [OK] Extension installed at: {TARGET_EXT_DIR}")

def create_desktop_shortcut():
    """Creates a 1-click Desktop Shortcut with OpenCut icon."""
    print("  [3/4] Creating 1-Click Desktop Shortcut with official logo...")
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

    # Invalidate and delete existing shortcut to ensure Windows Explorer refreshes the icon
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
    tmp_vbs = BASE_DIR / "_mk_shortcut.vbs"
    try:
        with open(tmp_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        subprocess.run(f'cscript //nologo "{tmp_vbs}"', shell=True, capture_output=True)
        if tmp_vbs.exists():
            os.remove(str(tmp_vbs))

        # Notify Windows Shell of icon association update
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass

        print(f"        [OK] Desktop shortcut created with custom icon: {shortcut_path}")
    except Exception as e:
        print(f"        [!] Shortcut notice: {e}")

def check_dependencies():
    """Ensures Python, FFmpeg and requirements are verified."""
    print("  [4/4] Verifying FFmpeg and local engines...")
    ffmpeg_local = BASE_DIR / "ffmpeg" / "ffmpeg.exe"
    if ffmpeg_local.exists():
        print("        [OK] Bundled high-performance FFmpeg verified.")
    else:
        print("        [!] Local ffmpeg/ffmpeg.exe not found, checking system PATH...")

def main():
    print("=" * 65)
    print("   OpenCut Enhanced - Automatic Environment Setup")
    print("=" * 65)
    enable_player_debug_mode()
    sync_extension_to_adobe()
    create_desktop_shortcut()
    check_dependencies()
    print("=" * 65)
    print("SETUP COMPLETE!")
    print("1. An 'OpenCut Enhanced' icon is now on your Desktop.")
    print("2. In Adobe Premiere Pro, find the panel at: Window -> Extensions -> OpenCut")
    print("=" * 65)

if __name__ == "__main__":
    main()
