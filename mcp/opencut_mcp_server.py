#!/usr/bin/env python3
"""
OpenCut MCP Server (Model Context Protocol)
Exposes OpenCut's Video Editing and HyperFrames Generative Pipeline to AI Agents
(Antigravity, Claude Code, Cursor, etc.) via JSON-RPC 2.0 stdio.

Supported Tools:
- hyperframes_generate_video: End-to-end AI video (script -> voiceover -> HTML/GSAP -> render -> sound design -> snapshot)
- hyperframes_render: Render a HyperFrames project to MP4
- hyperframes_snapshot: Capture frame snapshot grid (contact-sheet.jpg) for visual QA
- opencut_sound_design: Micro-timed BPT SFX stem + EBU R128 loudness matching & ducking
- opencut_generate_voiceover: Neural TTS voiceover with word-level VTT timestamps
- opencut_get_timeline_config: Generate Premiere Pro multi-track import payload (V1, A1, A2, A3, V2)
"""

import sys
import os
import io
import json
import traceback
from pathlib import Path

# Fix Windows console encoding for UTF-8 stdio
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path("E:/autocut")
SERVER_DIR = BASE_DIR / "server"
sys.path.insert(0, str(SERVER_DIR))

try:
    from hyperframes_pipeline import create_ai_video, generate_voiceover, run_cmd
except ImportError as e:
    sys.stderr.write(f"Warning: Failed to import hyperframes_pipeline: {e}\n")
    create_ai_video = None

try:
    from sound_designer import design_soundtrack, PALETTES
except ImportError as e:
    sys.stderr.write(f"Warning: Failed to import sound_designer: {e}\n")
    design_soundtrack = None
    PALETTES = {}

try:
    from pipeline import run_pipeline
except ImportError as e:
    sys.stderr.write(f"Warning: Failed to import pipeline: {e}\n")
    run_pipeline = None

TOOLS_REGISTRY = [
    {
        "name": "opencut_smart_cut",
        "description": "Run the autonomous 10-step video editing pipeline: media probe, silence detection (-30dB), filler words & repeated takes removal, word padding, CRF 18 render, ASS kinetic captions, vertical 9:16 framing, and 5-frame QA verification.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to input video file."
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, previews cuts without rendering. Always run this first!",
                    "default": False
                },
                "vertical": {
                    "type": "boolean",
                    "description": "If true, center crops to 1080x1920 (9:16 portrait).",
                    "default": False
                },
                "normalize": {
                    "type": "boolean",
                    "description": "If true, normalizes loudness to -16 LUFS (EBU R128).",
                    "default": False
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional custom output video path."
                }
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "hyperframes_generate_video",
        "description": "Generate an animated video from a topic or script using HeyGen's HyperFrames engine. Produces multi-track assets (Video V1, Voiceover A1, SFX Stem A3, Captions V2) and visual contact-sheet QA images.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic, headline or core theme for the video (e.g., '5 AI Tools for Video Editors')."
                },
                "script": {
                    "type": "string",
                    "description": "Optional custom voiceover script. If not provided, an engaging punchy script is automatically composed."
                },
                "voice": {
                    "type": "string",
                    "description": "TTS voice name (default: 'en-US-ChristopherNeural'). Options: 'en-US-GuyNeural', 'en-US-JennyNeural', 'en-US-AriaNeural', 'bn-BD-PradeepNeural', etc.",
                    "default": "en-US-ChristopherNeural"
                },
                "aspect": {
                    "type": "string",
                    "description": "Video resolution aspect ratio: 'portrait' (1080x1920 9:16 for Reels/Shorts/TikTok) or 'landscape' (1920x1080 16:9 for YouTube).",
                    "enum": ["portrait", "landscape"],
                    "default": "portrait"
                },
                "genre": {
                    "type": "string",
                    "description": "Smart sound design palette: 'reels' (fast whooshes, pops), 'gaming' (heavy risers, 808 booms), 'tutorial' (clean tech chimes), 'vlog' (soft swooshes), 'cinematic' (sub braams).",
                    "enum": ["reels", "gaming", "tutorial", "vlog", "cinematic"],
                    "default": "reels"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional custom folder path to save project code, audio, and renders."
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "hyperframes_render",
        "description": "Render an existing HyperFrames composition project to an MP4 video file using Headless Chromium and FFmpeg.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_dir": {
                    "type": "string",
                    "description": "Absolute directory path containing index.html and hyperframes.json."
                },
                "output_name": {
                    "type": "string",
                    "description": "Output video file name (default: 'out.mp4').",
                    "default": "out.mp4"
                }
            },
            "required": ["project_dir"]
        }
    },
    {
        "name": "hyperframes_snapshot",
        "description": "Capture a visual contact sheet (grid of frame screenshots) from a HyperFrames composition for visual inspection, typography validation, and QA.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_dir": {
                    "type": "string",
                    "description": "Absolute directory path containing index.html and hyperframes.json."
                }
            },
            "required": ["project_dir"]
        }
    },
    {
        "name": "opencut_sound_design",
        "description": "Run professional content-aware Sound Design on any video file. Analyzes cuts, punches, and energy to generate a sample-accurate SFX stem, balanced dialogue, and ducked background music.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Absolute path to input video file."
                },
                "genre": {
                    "type": "string",
                    "description": "Sound design palette style: 'gaming', 'reels', 'vlog', 'tutorial', 'cinematic'.",
                    "default": "gaming"
                },
                "intensity": {
                    "type": "string",
                    "description": "SFX density: 'subtle', 'balanced', 'hype'.",
                    "default": "balanced"
                },
                "music_path": {
                    "type": "string",
                    "description": "Optional path to background music file for dynamic audio ducking."
                },
                "music_vol": {
                    "type": "number",
                    "description": "Background music volume multiplier (0.05 to 0.80, default: 0.25).",
                    "default": 0.25
                },
                "duck_amount": {
                    "type": "number",
                    "description": "Amount to duck music when dialogue is active (0.20 to 0.95, default: 0.70).",
                    "default": 0.70
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional output directory."
                }
            },
            "required": ["video_path"]
        }
    },
    {
        "name": "opencut_generate_voiceover",
        "description": "Generate natural neural TTS speech voiceover along with word-level SRT/VTT subtitle timestamps using edge-tts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Script text to speak."
                },
                "voice": {
                    "type": "string",
                    "description": "TTS voice name (default: 'en-US-ChristopherNeural').",
                    "default": "en-US-ChristopherNeural"
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save generated voice.mp3 and voice.vtt."
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "opencut_get_timeline_config",
        "description": "Generates a complete multi-track timeline configuration payload ready for importMultiTrackToTimeline in Premiere Pro (Video V1, Dialogue A1, Music A2, SFX Stem A3, Captions V2).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to primary video file."
                },
                "dialogue_path": {
                    "type": "string",
                    "description": "Optional path to isolated dialogue/voiceover track (placed on A1)."
                },
                "music_path": {
                    "type": "string",
                    "description": "Optional path to background music (placed on A2)."
                },
                "sfx_path": {
                    "type": "string",
                    "description": "Optional path to synchronized SFX stem (placed on A3)."
                },
                "srt_path": {
                    "type": "string",
                    "description": "Optional path to subtitle/caption file (placed on V2/Subtitle track)."
                },
                "seq_name": {
                    "type": "string",
                    "description": "Custom sequence name in Premiere Pro."
                }
            },
            "required": ["video_path"]
        }
    }
]

def handle_tool_call(tool_name, arguments):
    """Execute requested tool and return standard MCP content dict."""
    if tool_name == "opencut_smart_cut":
        if not run_pipeline:
            raise RuntimeError("pipeline module not available")
        filepath = arguments.get("filepath")
        dry_run = bool(arguments.get("dry_run", False))
        vertical = bool(arguments.get("vertical", False))
        normalize = bool(arguments.get("normalize", False))
        output_path = arguments.get("output_path")

        result = run_pipeline(
            filepath=filepath,
            output_path=output_path,
            dry_run=dry_run,
            vertical=vertical,
            normalize=normalize
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }

    elif tool_name == "hyperframes_generate_video":
        if not create_ai_video:
            raise RuntimeError("hyperframes_pipeline module not available")
        
        topic = arguments.get("topic")
        script = arguments.get("script")
        voice = arguments.get("voice", "en-US-ChristopherNeural")
        aspect = arguments.get("aspect", "portrait")
        genre = arguments.get("genre", "reels")
        out_dir = arguments.get("output_dir")

        result = create_ai_video(
            topic=topic,
            script=script,
            voice=voice,
            aspect=aspect,
            sound_genre=genre,
            out_dir=out_dir
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }

    elif tool_name == "hyperframes_render":
        project_dir = arguments.get("project_dir")
        out_name = arguments.get("output_name", "out.mp4")
        if not os.path.exists(project_dir):
            raise FileNotFoundError(f"Directory not found: {project_dir}")
        
        cmd = f'npx hyperframes render -o "{out_name}"'
        code, stdout, stderr = run_cmd(cmd, cwd=project_dir)
        out_path = Path(project_dir) / out_name
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "success": code == 0 and out_path.exists(),
                        "exit_code": code,
                        "output_file": str(out_path) if out_path.exists() else None,
                        "stdout": stdout,
                        "stderr": stderr
                    }, indent=2)
                }
            ]
        }

    elif tool_name == "hyperframes_snapshot":
        project_dir = arguments.get("project_dir")
        if not os.path.exists(project_dir):
            raise FileNotFoundError(f"Directory not found: {project_dir}")
        
        cmd = "npx hyperframes snapshot"
        code, stdout, stderr = run_cmd(cmd, cwd=project_dir)
        contact_sheet = None
        for p in Path(project_dir).glob("**/*contact-sheet.jpg"):
            contact_sheet = str(p.resolve())
            break
            
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "success": code == 0,
                        "contact_sheet": contact_sheet,
                        "stdout": stdout,
                        "stderr": stderr
                    }, indent=2)
                }
            ]
        }

    elif tool_name == "opencut_sound_design":
        if not design_soundtrack:
            raise RuntimeError("sound_designer module not available")
        
        video_path = arguments.get("video_path")
        genre = arguments.get("genre", "gaming")
        intensity = arguments.get("intensity", "balanced")
        music_path = arguments.get("music_path")
        music_vol = float(arguments.get("music_vol", 0.25))
        duck_amount = float(arguments.get("duck_amount", 0.70))
        output_dir = arguments.get("output_dir")

        res = design_soundtrack(
            video_path=video_path,
            genre=genre,
            intensity=intensity,
            music_path=music_path,
            music_vol=music_vol,
            duck_amount=duck_amount,
            output_dir=output_dir
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(res, indent=2)
                }
            ]
        }

    elif tool_name == "opencut_generate_voiceover":
        text = arguments.get("text")
        voice = arguments.get("voice", "en-US-ChristopherNeural")
        out_dir = Path(arguments.get("output_dir") or (BASE_DIR / "projects" / "voiceover"))
        out_dir.mkdir(parents=True, exist_ok=True)
        
        audio_file = out_dir / "voice.mp3"
        vtt_file = out_dir / "voice.vtt"
        generate_voiceover(text, voice=voice, out_audio=str(audio_file), out_vtt=str(vtt_file))
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "status": "success",
                        "audio_path": str(audio_file.resolve()),
                        "vtt_path": str(vtt_file.resolve()),
                        "voice": voice,
                        "text": text
                    }, indent=2)
                }
            ]
        }

    elif tool_name == "opencut_get_timeline_config":
        v_path = arguments.get("video_path")
        d_path = arguments.get("dialogue_path")
        m_path = arguments.get("music_path")
        s_path = arguments.get("sfx_path")
        srt_path = arguments.get("srt_path")
        seq_name = arguments.get("seq_name")

        cfg = {
            "videoPath": v_path,
            "dialoguePath": d_path,
            "musicPath": m_path,
            "sfxPath": s_path,
            "srtPath": srt_path,
            "seqName": seq_name or f"OpenCut - {Path(v_path).stem}",
            "placeIndividualSfx": True
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(cfg, indent=2)
                }
            ]
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")

def send_response(response_dict):
    """Write JSON-RPC response to stdout and flush."""
    body = json.dumps(response_dict)
    sys.stdout.write(body + "\n")
    sys.stdout.flush()

def main():
    sys.stderr.write("OpenCut MCP Server started on stdio.\n")
    sys.stderr.flush()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Handle possible Content-Length prefix (LSP/MCP stdio framing)
            if line.startswith("Content-Length:"):
                length = int(line.split(":")[1].strip())
                # Read until blank line
                while True:
                    sep = sys.stdin.readline().strip()
                    if not sep:
                        break
                payload = sys.stdin.read(length)
                req = json.loads(payload)
            else:
                req = json.loads(line)

            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "opencut-video-engine",
                            "version": "1.0.0"
                        }
                    }
                })

            elif method == "notifications/initialized":
                # Client acknowledgment, no reply needed
                pass

            elif method == "ping":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {}
                })

            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": TOOLS_REGISTRY
                    }
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                try:
                    tool_res = handle_tool_call(tool_name, arguments)
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": tool_res
                    })
                except Exception as err:
                    err_msg = f"{type(err).__name__}: {str(err)}\n{traceback.format_exc()}"
                    sys.stderr.write(f"Error calling tool {tool_name}: {err_msg}\n")
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error executing {tool_name}: {err_msg}"}],
                            "isError": True
                        }
                    })

            else:
                if req_id is not None:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    })

        except Exception as e:
            sys.stderr.write(f"MCP Server Loop Error: {e}\n{traceback.format_exc()}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
