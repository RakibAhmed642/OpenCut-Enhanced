"""
OpenCut Extension Synchronizer & Live Reloader
Synchronizes workspace files to client/dist and Adobe CEP extensions folder,
then triggers an instant hot-reload via CEP DevTools WebSocket (Port 8842).
"""

import os
import sys
import json
import shutil
import urllib.request
from pathlib import Path

WORKSPACE_EXT = Path(r"E:\autocut\extension\com.opencut.panel")
CLIENT_SRC = WORKSPACE_EXT / "client"
CLIENT_DIST = WORKSPACE_EXT / "client" / "dist"
ADOBE_EXT = Path(r"C:\Users\h\AppData\Roaming\Adobe\CEP\extensions\com.opencut.panel")

def sync_files():
    print("[1/3] Syncing workspace client -> client/dist...")
    if not CLIENT_DIST.exists():
        CLIENT_DIST.mkdir(parents=True, exist_ok=True)

    for item in CLIENT_SRC.iterdir():
        if item.name == "dist":
            continue
        if item.is_file():
            shutil.copy2(item, CLIENT_DIST / item.name)
        elif item.is_dir() and item.name in ["locales", "assets"]:
            shutil.copytree(item, CLIENT_DIST / item.name, dirs_exist_ok=True)

    print("[2/3] Syncing workspace -> Adobe CEP extensions folder...")
    if ADOBE_EXT.exists():
        shutil.copytree(WORKSPACE_EXT, ADOBE_EXT, dirs_exist_ok=True)
    else:
        shutil.copytree(WORKSPACE_EXT, ADOBE_EXT)

    print("[3/3] Triggering live reload in Premiere Pro panel (Port 8842)...")
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8842/json", timeout=2)
        targets = json.loads(req.read().decode("utf-8"))
        if targets and len(targets) > 0:
            ws_url = targets[0].get("webSocketDebuggerUrl")
            if ws_url:
                jsx_esc = str(ADOBE_EXT / "host" / "index.jsx").replace("\\", "/")
                reload_js = f'''
                    if (window.__adobe_cep__) {{
                        window.__adobe_cep__.evalScript("try {{ $.evalFile('{jsx_esc}'); 'OK'; }} catch(e) {{ e.toString(); }}", function(res) {{
                            console.log("JSX evalFile reloaded:", res);
                            window.location.reload();
                        }});
                    }} else {{
                        window.location.reload();
                    }}
                '''
                try:
                    import websocket
                    ws = websocket.create_connection(ws_url, timeout=2)
                    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": reload_js}}))
                    ws.close()
                    print(">> Live reload & JSX reload triggered successfully in Premiere Pro!")
                except Exception as ws_err:
                    print(f"WebSocket send notice: {ws_err}")
            else:
                print("DevTools target found but no WebSocket URL.")
        else:
            print("No active CEP DevTools page found (panel may be closed).")
    except Exception as e:
        print(f"Notice: DevTools reload not available: {e}")

    print("Sync complete.")

if __name__ == "__main__":
    sync_files()
