"""
OpenCut Sound Designer Service
Lightweight HTTP micro-service running on 127.0.0.1:5682.
Zero external dependencies (pure Python standard library).
"""

import sys
import os
import json
import traceback
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))
from sound_designer import design_soundtrack, ensure_sound_library, PALETTES, ASSETS_DIR
from hyperframes_pipeline import create_ai_video, run_cmd
from youtube_agent_engine import execute_youtube_ready_agent

PORT = 5682

VOICES = [
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US Male - Professional / Confident)", "lang": "en-US"},
    {"id": "en-US-GuyNeural", "name": "Guy (US Male - Energetic / Casual)", "lang": "en-US"},
    {"id": "en-US-JennyNeural", "name": "Jenny (US Female - Natural / Conversational)", "lang": "en-US"},
    {"id": "en-US-AriaNeural", "name": "Aria (US Female - Expressive / Dynamic)", "lang": "en-US"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female - Elegant / Polished)", "lang": "en-GB"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male - Informative / Crisp)", "lang": "en-GB"},
    {"id": "bn-BD-PradeepNeural", "name": "Pradeep (Bengali Male)", "lang": "bn-BD"},
    {"id": "bn-BD-NabanitaNeural", "name": "Nabanita (Bengali Female)", "lang": "bn-BD"}
]

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class SoundDesignerHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-OpenCut-Token, *")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = self.path.split("?")[0]
        if parsed_path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            resp = {
                "status": "ok",
                "service": "opencut-ai-studio-service",
                "port": PORT,
                "genres": list(PALETTES.keys()),
                "voices": len(VOICES)
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif parsed_path == "/palettes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(PALETTES).encode("utf-8"))
        elif parsed_path == "/hyperframes/voices":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(VOICES).encode("utf-8"))
        elif parsed_path == "/system/ai-config":
            try:
                from ai_moment_intelligence import load_ai_config
                cfg = load_ai_config()
                masked_cfg = dict(cfg)
                raw_key = masked_cfg.get("api_key", "")
                if raw_key:
                    if len(raw_key) > 8:
                        masked_cfg["api_key_masked"] = raw_key[:4] + "••••••••" + raw_key[-4:]
                    else:
                        masked_cfg["api_key_masked"] = "••••••••"
                    masked_cfg["has_key"] = True
                else:
                    masked_cfg["api_key_masked"] = ""
                    masked_cfg["has_key"] = False
                masked_cfg["api_key"] = ""  # never expose raw key over GET

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(masked_cfg).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif parsed_path == "/captions/youtuber-styles":
            try:
                from keyword_cues_engine import YOUTUBER_STYLES
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"styles": YOUTUBER_STYLES}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif parsed_path == "/system/skills":
            try:
                from agent_skills_service import list_skills
                skills = list_skills()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "skills": skills}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif parsed_path == "/file":
            # Serve local file (e.g. contact-sheet.jpg) for panel preview
            import urllib.parse
            query_str = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = urllib.parse.parse_qs(query_str)
            target = params.get("path", [None])[0]
            if target and os.path.exists(target) and os.path.isfile(target):
                mime = "image/jpeg"
                if target.lower().endswith(".png"): mime = "image/png"
                elif target.lower().endswith(".mp4"): mime = "video/mp4"
                elif target.lower().endswith(".vtt"): mime = "text/vtt"
                
                try:
                    with open(target, "rb") as f:
                        file_data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(file_data)))
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(file_data)
                    return
                except Exception as fe:
                    self.send_response(500)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(str(fe).encode("utf-8"))
                    return
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
        elif parsed_path == "/media/search":
            import urllib.parse
            query_str = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = urllib.parse.parse_qs(query_str)
            m_type = params.get("type", ["video"])[0]
            q = params.get("query", [""])[0] or params.get("q", [""])[0]
            cat = params.get("category", [""])[0]
            limit = int(params.get("limit", [20])[0])
            try:
                from free_media_service import search_free_media
                results = search_free_media(media_type=m_type, query=q, category=cat, limit=limit)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "count": len(results), "results": results}).encode("utf-8"))
            except Exception as me:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(me)}).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_POST(self):
        if self.path == "/sound/design":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            video_path = data.get("filepath")
            if not video_path or not os.path.exists(video_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {video_path}"}).encode("utf-8"))
                return

            genre = data.get("genre", "gaming")
            intensity = data.get("intensity", "balanced")
            music_path = data.get("music_path")
            music_vol = float(data.get("music_vol", 0.25))
            duck_amount = float(data.get("duck_amount", 0.70))
            output_dir = data.get("output_dir")

            try:
                result = design_soundtrack(
                    video_path,
                    genre=genre,
                    intensity=intensity,
                    music_path=music_path,
                    music_vol=music_vol,
                    duck_amount=duck_amount,
                    output_dir=output_dir
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/hyperframes/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            topic = data.get("topic")
            if not topic:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing topic parameter"}).encode("utf-8"))
                return

            script = data.get("script") or None
            voice = data.get("voice", "en-US-ChristopherNeural")
            aspect = data.get("aspect", "portrait")
            genre = data.get("genre", "reels")
            out_dir = data.get("output_dir") or None

            try:
                result = create_ai_video(
                    topic=topic,
                    script=script,
                    voice=voice,
                    aspect=aspect,
                    sound_genre=genre,
                    out_dir=out_dir
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/hyperframes/render":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            project_dir = data.get("project_dir")
            out_name = data.get("output_name", "out.mp4")
            if not project_dir or not os.path.exists(project_dir):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Directory not found: {project_dir}"}).encode("utf-8"))
                return

            cmd = f'npx hyperframes render -o "{out_name}"'
            code, stdout, stderr = run_cmd(cmd, cwd=project_dir)
            out_file = Path(project_dir) / out_name
            self.send_response(200 if code == 0 else 500)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": code == 0,
                "video_path": str(out_file) if out_file.exists() else None,
                "stdout": stdout,
                "stderr": stderr
            }).encode("utf-8"))

        elif self.path == "/reels/analyze":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            video_path = data.get("filepath") or data.get("video_path") or data.get("media_path")
            if not video_path or not os.path.exists(video_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {video_path}"}).encode("utf-8"))
                return

            language = data.get("language", "auto")
            method = data.get("method", "both")
            raw_duration = data.get("target_duration") if data.get("target_duration") is not None else data.get("duration")
            target_duration = float(raw_duration) if raw_duration not in ("full", 0, "0", None) else 30.0
            ai_mode = data.get("ai_mode", "auto")
            ai_provider = data.get("ai_provider")
            api_key = data.get("api_key")
            ai_model = data.get("ai_model")
            custom_endpoint = data.get("custom_endpoint")
            ai_allow_videos = bool(data.get("ai_allow_videos", True))
            ai_allow_sfx = bool(data.get("ai_allow_sfx", True))
            ai_allow_gifs = bool(data.get("ai_allow_gifs", True))
            ai_allow_motion = bool(data.get("ai_allow_motion", True))

            try:
                from auto_reels_engine import analyze_viral_candidates
                result = analyze_viral_candidates(
                    filepath=video_path,
                    language=language,
                    method=method,
                    target_duration=target_duration,
                    ai_mode=ai_mode,
                    ai_provider=ai_provider,
                    api_key=api_key,
                    ai_model=ai_model,
                    custom_endpoint=custom_endpoint,
                    ai_allow_videos=ai_allow_videos,
                    ai_allow_sfx=ai_allow_sfx,
                    ai_allow_gifs=ai_allow_gifs,
                    ai_allow_motion=ai_allow_motion
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "traceback": err_trace}).encode("utf-8"))

        elif self.path == "/reels/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            video_path = data.get("filepath") or data.get("video_path") or data.get("media_path")
            if not video_path or not os.path.exists(video_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {video_path}"}).encode("utf-8"))
                return

            raw_duration = data.get("target_duration") if data.get("target_duration") is not None else data.get("duration")
            target_duration = float(raw_duration) if raw_duration not in ("full", 0, "0", None) else 0.0
            aspect_ratio = data.get("aspect_ratio", "9:16")
            layout_mode = data.get("layout_mode", "crop_center")
            remove_silence = bool(data.get("remove_silence", True))
            auto_zoom = bool(data.get("auto_zoom", True))
            zoom_style = str(data.get("zoom_style", "jump"))
            zoom_scale = float(data.get("zoom_scale", 1.18))
            sound_design = bool(data.get("sound_design", True))
            sound_genre = data.get("sound_genre", "gaming")
            sound_intensity = data.get("sound_intensity", "balanced")
            add_captions = bool(data.get("add_captions", True))
            caption_style = data.get("caption_style", "bold_yellow")
            whisper_model = data.get("whisper_model", "base")
            output_dir = data.get("output_dir") or None
            start_time = data.get("start_time") if data.get("start_time") is not None else data.get("start")
            end_time = data.get("end_time") if data.get("end_time") is not None else data.get("end")
            language = data.get("language", "auto")
            burn_captions = bool(data.get("burn_captions", True))
            ai_caption_polish = bool(data.get("ai_caption_polish", False))
            ai_provider = data.get("ai_provider")
            api_key = data.get("api_key")
            ai_model = data.get("ai_model")
            custom_endpoint = data.get("custom_endpoint")

            try:
                from auto_reels_engine import create_auto_reel
                result = create_auto_reel(
                    filepath=video_path,
                    target_duration=target_duration,
                    aspect_ratio=aspect_ratio,
                    layout_mode=layout_mode,
                    remove_silence=remove_silence,
                    auto_zoom=auto_zoom,
                    zoom_style=zoom_style,
                    zoom_scale=zoom_scale,
                    sound_design=sound_design,
                    sound_genre=sound_genre,
                    sound_intensity=sound_intensity,
                    add_captions=add_captions,
                    caption_style=caption_style,
                    whisper_model=whisper_model,
                    output_dir=output_dir,
                    start_time=float(start_time) if start_time is not None else None,
                    end_time=float(end_time) if end_time is not None else None,
                    language=language,
                    burn_captions=burn_captions,
                    ai_caption_polish=ai_caption_polish,
                    ai_provider=ai_provider,
                    api_key=api_key,
                    ai_model=ai_model,
                    custom_endpoint=custom_endpoint
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/hook/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            video_path = data.get("filepath") or data.get("video_path") or data.get("media_path")
            if not video_path or not os.path.exists(video_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {video_path}"}).encode("utf-8"))
                return

            clip_count = int(data.get("clip_count", 3))
            clip_duration = float(data.get("clip_duration", 2.5))
            hook_style = str(data.get("style") or data.get("hook_style") or "flash")
            badge_text = str(data.get("badge_text", "COMING UP..."))
            transition_sfx = bool(data.get("sfx", "whoosh") != "none" if "sfx" in data else data.get("transition_sfx", True))
            flash_cuts = bool(hook_style != "cut")
            output_dir = data.get("output_dir") or None
            use_ai = bool(data.get("use_ai", False))
            ai_provider = data.get("ai_provider")
            api_key = data.get("api_key")
            ai_model = data.get("ai_model")
            custom_endpoint = data.get("custom_endpoint")

            try:
                from hook_engine import create_smart_hook
                result = create_smart_hook(
                    filepath=video_path,
                    clip_count=clip_count,
                    clip_duration=clip_duration,
                    hook_style=hook_style,
                    badge_text=badge_text,
                    transition_sfx=transition_sfx,
                    flash_cuts=flash_cuts,
                    output_dir=output_dir,
                    use_ai=use_ai,
                    ai_provider=ai_provider,
                    api_key=api_key,
                    ai_model=ai_model,
                    custom_endpoint=custom_endpoint
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/system/reveal":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                p = data.get("path")
                if not p:
                    raise ValueError("No path provided")
                clean_p = os.path.normpath(str(p).strip('\"\''))
                if os.path.isfile(clean_p):
                    subprocess.Popen(f'explorer.exe /select,"{clean_p}"')
                elif os.path.isdir(clean_p):
                    os.startfile(clean_p)
                else:
                    parent_dir = os.path.dirname(clean_p)
                    if os.path.exists(parent_dir):
                        reels = sorted(Path(parent_dir).glob("*reel*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
                        if reels:
                            subprocess.Popen(f'explorer.exe /select,"{reels[0]}"')
                        else:
                            os.startfile(parent_dir)
                    else:
                        raise FileNotFoundError(f"Path not found: {clean_p}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/play":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                p = data.get("path")
                if not p:
                    raise ValueError("No path provided")
                clean_p = os.path.normpath(str(p).strip('\"\''))
                if not os.path.exists(clean_p):
                    parent = os.path.dirname(clean_p)
                    if os.path.exists(parent):
                        reels = sorted(Path(parent).glob("*reel*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
                        if reels:
                            clean_p = str(reels[0])
                        else:
                            raise FileNotFoundError(f"File not found: {clean_p}")
                    else:
                        raise FileNotFoundError(f"File not found: {clean_p}")
                
                # Check for installed players: VLC, Windows Media Player, or system default
                vlc_candidates = [
                    r"D:\VLC\vlc.exe",
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ]
                vlc_bin = next((v for v in vlc_candidates if os.path.exists(v)), None)
                if vlc_bin:
                    # Clean up any zombie VLC headless process with no window
                    try:
                        subprocess.run('powershell -Command "Get-Process -Name vlc -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -eq 0 } | Stop-Process -Force -ErrorAction SilentlyContinue"', shell=True, timeout=2)
                    except Exception:
                        pass
                    subprocess.Popen([vlc_bin, clean_p])
                else:
                    try:
                        subprocess.Popen(f'explorer.exe "{clean_p}"')
                    except Exception:
                        os.startfile(clean_p)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "played": clean_p}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/ai-config":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                from ai_moment_intelligence import save_ai_config, load_ai_config
                cur = load_ai_config()
                if "api_key" in data and not str(data["api_key"]).strip() and cur.get("api_key"):
                    del data["api_key"]
                save_ai_config(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "AI configuration saved"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/skills/save":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                from agent_skills_service import save_skill
                saved = save_skill(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "skill": saved}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/skills/delete":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                sk_id = data.get("id") or data.get("skill_id")
                from agent_skills_service import delete_skill
                ok = delete_skill(sk_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "deleted": ok}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/ai-verify":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                from ai_moment_intelligence import verify_ai_provider, load_ai_config
                provider = data.get("provider", "gemini")
                api_key = data.get("api_key", "").strip()
                if not api_key:
                    cur = load_ai_config()
                    api_key = cur.get("api_key", "")
                model = data.get("model", "")
                custom_endpoint = data.get("custom_endpoint", "")
                ver_res = verify_ai_provider(provider, api_key, model=model, custom_endpoint=custom_endpoint)
                status_code = 200 if ver_res.get("status") == "success" else 400
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(ver_res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/system/ai-metadata":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                video_path = data.get("filepath") or data.get("video_path")
                transcript_input = data.get("transcript")
                source = transcript_input if (isinstance(transcript_input, list) and transcript_input) else video_path
                if not source or (isinstance(source, str) and not os.path.exists(source)):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"File not found: {source}"}).encode("utf-8"))
                    return

                from ai_moment_intelligence import generate_social_metadata_llm
                result = generate_social_metadata_llm(
                    filepath_or_transcript=source,
                    language=data.get("language", "auto"),
                    provider=data.get("provider"),
                    api_key=data.get("api_key"),
                    model=data.get("model"),
                    custom_endpoint=data.get("custom_endpoint")
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/system/ai-assistant":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
                video_path = data.get("filepath") or data.get("video_path")
                transcript_input = data.get("transcript")
                source = transcript_input if (isinstance(transcript_input, list) and transcript_input) else video_path
                query = data.get("query", "").strip()
                if not source or (isinstance(source, str) and not os.path.exists(source)):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"File not found: {source}"}).encode("utf-8"))
                    return
                if not query:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Query string is required"}).encode("utf-8"))
                    return

                from ai_moment_intelligence import query_video_assistant_llm
                result = query_video_assistant_llm(
                    filepath_or_transcript=source,
                    user_query=query,
                    provider=data.get("provider"),
                    api_key=data.get("api_key"),
                    model=data.get("model"),
                    custom_endpoint=data.get("custom_endpoint")
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/audio/waveform":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            filepath = data.get("file") or data.get("filepath")
            if not filepath:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No file path provided"}).encode("utf-8"))
                return

            samples = int(data.get("samples", 600))
            threshold_db = float(data.get("threshold_db", -30.0))

            try:
                result = extract_audio_waveform(filepath, num_samples=samples, threshold_db=threshold_db)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/media/download":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            media_url = data.get("url") or data.get("filepath")
            title = data.get("title", "media_asset")
            m_type = data.get("type", "video")

            if not media_url:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing media url parameter"}).encode("utf-8"))
                return

            try:
                from free_media_service import download_and_prepare_media
                prepared = download_and_prepare_media(media_url, title=title, media_type=m_type)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(prepared).encode("utf-8"))
            except Exception as de:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(de), "trace": err_trace}).encode("utf-8"))

        elif self.path == "/captions/keyword-cues":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            try:
                from keyword_cues_engine import spot_keywords_and_generate_cues
                filepath = data.get("filepath")
                target_words = data.get("target_words", [])
                output_dir = data.get("output_dir")
                options = data.get("options", {})
                res = spot_keywords_and_generate_cues(filepath, target_words, output_dir=output_dir, options=options)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        elif self.path == "/agent/youtube-ready":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len)
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            video_path = data.get("filepath") or data.get("video_path")
            if not video_path or not os.path.exists(video_path):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"File not found: {video_path}"}).encode("utf-8"))
                return

            output_dir = data.get("output_dir")
            options = data.get("options") or {}

            try:
                result = execute_youtube_ready_agent(video_path, output_dir=output_dir, options=options)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                err_trace = traceback.format_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "trace": err_trace}).encode("utf-8"))

        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

def extract_audio_waveform(file_path, num_samples=600, threshold_db=-30.0):
    import math, struct
    clean_p = os.path.normpath(str(file_path).strip('\"\''))
    if not os.path.exists(clean_p):
        raise FileNotFoundError(f"File not found: {clean_p}")

    ffmpeg_bin = r"E:\autocut\ffmpeg\ffmpeg.exe"
    ffprobe_bin = r"E:\autocut\ffmpeg\ffprobe.exe"
    if not os.path.exists(ffmpeg_bin):
        import shutil
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    if not os.path.exists(ffprobe_bin):
        import shutil
        ffprobe_bin = shutil.which("ffprobe") or "ffprobe"

    # 1. Probe duration & audio stream
    probe_cmd = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration:stream=codec_type",
        "-of", "json",
        clean_p
    ]
    res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_info = json.loads(res.stdout)
    duration = float(probe_info.get("format", {}).get("duration", 0))
    streams = probe_info.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    if not has_audio or duration <= 0:
        return {
            "duration": duration,
            "has_audio": False,
            "peaks": [],
            "peaks_db": [],
            "silences": [],
            "silence_duration": 0,
            "speech_duration": 0,
            "reduction_percent": 0
        }

    # 2. Extract 8000Hz 16-bit mono PCM via FFmpeg stdout stream
    ffmpeg_cmd = [
        ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
        "-i", clean_p,
        "-vn", "-ac", "1", "-ar", "8000",
        "-f", "s16le", "-"
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw_pcm, _ = proc.communicate()

    total_samples = len(raw_pcm) // 2
    if total_samples == 0:
        return {
            "duration": duration,
            "has_audio": True,
            "peaks": [],
            "peaks_db": [],
            "silences": [],
            "silence_duration": 0,
            "speech_duration": 0,
            "reduction_percent": 0
        }

    samples_per_bar = max(1, total_samples // num_samples)
    actual_bars = total_samples // samples_per_bar

    peaks = []
    peaks_db = []

    for i in range(actual_bars):
        start_byte = i * samples_per_bar * 2
        end_byte = min(len(raw_pcm), (i + 1) * samples_per_bar * 2)
        chunk = raw_pcm[start_byte:end_byte]
        num_shorts = len(chunk) // 2
        if num_shorts == 0:
            continue
        shorts = struct.unpack(f"<{num_shorts}h", chunk)

        max_val = max(abs(s) for s in shorts) / 32768.0
        rms_val = math.sqrt(sum(s * s for s in shorts) / num_shorts) / 32768.0

        # 75% Peak + 25% RMS for balanced, accurate dynamics
        combined = 0.75 * max_val + 0.25 * rms_val
        if combined > 1e-5:
            db = 20.0 * math.log10(combined)
        else:
            db = -60.0
        db = max(-60.0, min(0.0, db))

        # Perceptual height (0.02 minimum so silent bars are slightly visible on canvas)
        height = max(0.02, (db + 50.0) / 50.0) if db > -50.0 else 0.02

        peaks.append(round(height, 4))
        peaks_db.append(round(db, 1))

    # 3. Detect exact silence intervals
    time_per_bar = duration / len(peaks)
    silences = []
    in_silence = False
    silence_start = 0.0
    total_silence_time = 0.0

    for i, db in enumerate(peaks_db):
        t = i * time_per_bar
        if db < threshold_db:
            if not in_silence:
                in_silence = True
                silence_start = t
        else:
            if in_silence:
                in_silence = False
                sil_dur = t - silence_start
                if sil_dur >= 0.25:
                    silences.append({"start": round(silence_start, 2), "end": round(t, 2), "duration": round(sil_dur, 2)})
                    total_silence_time += sil_dur
    if in_silence:
        sil_dur = duration - silence_start
        if sil_dur >= 0.25:
            silences.append({"start": round(silence_start, 2), "end": round(duration, 2), "duration": round(sil_dur, 2)})
            total_silence_time += sil_dur

    speech_time = max(0.0, duration - total_silence_time)
    reduction = (total_silence_time / duration * 100.0) if duration > 0 else 0.0

    return {
        "duration": round(duration, 2),
        "has_audio": True,
        "num_peaks": len(peaks),
        "peaks": peaks,
        "peaks_db": peaks_db,
        "silences": silences,
        "silence_duration": round(total_silence_time, 2),
        "speech_duration": round(speech_time, 2),
        "reduction_percent": round(reduction, 1),
        "threshold_db": threshold_db
    }

def main():
    ensure_sound_library()
    server = ThreadedHTTPServer(("127.0.0.1", PORT), SoundDesignerHandler)
    print(f"OpenCut Sound Designer Service running on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == "__main__":
    main()
