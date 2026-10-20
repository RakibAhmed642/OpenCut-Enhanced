"""
OpenCut HyperFrames AI Video Generation Pipeline
Orchestrates: Topic/Idea -> Script -> Voiceover -> Timestamps -> HyperFrames HTML/GSAP -> Render -> Sound Design -> Premiere Pro.
"""

import os
import sys
import json
import math
import asyncio
import subprocess
import argparse
from pathlib import Path

# Paths
BASE_DIR = Path("E:/autocut")
FFMPEG = str(BASE_DIR / "ffmpeg" / "ffmpeg.exe")
FFPROBE = str(BASE_DIR / "ffmpeg" / "ffprobe.exe")
PROJECTS_DIR = BASE_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Add server dir to path for sound_designer
sys.path.insert(0, str(BASE_DIR / "server"))
try:
    from sound_designer import design_soundtrack
except ImportError:
    design_soundtrack = None

def run_cmd(cmd, cwd=None):
    """Run shell command and return returncode, stdout, stderr."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, cwd=cwd)
    return res.returncode, res.stdout, res.stderr

def get_audio_duration(file_path):
    """Get precise duration of audio file via ffprobe."""
    cmd = f'"{FFPROBE}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    code, out, _ = run_cmd(cmd)
    try:
        return float(out.strip())
    except:
        return 10.0

async def generate_voiceover_edge(text, voice="en-US-ChristopherNeural", out_audio="voice.mp3", out_vtt="voice.vtt"):
    """Generate high quality TTS voiceover and subtitle timing using edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    
    with open(out_audio, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
                
    with open(out_vtt, "w", encoding="utf-8") as file:
        file.write(submaker.get_srt())

def generate_voiceover(text, voice="en-US-ChristopherNeural", out_audio="voice.mp3", out_vtt="voice.vtt"):
    """Synchronous wrapper for voiceover generation."""
    asyncio.run(generate_voiceover_edge(text, voice, out_audio, out_vtt))

def parse_srt_words(srt_path):
    """Parse SRT/VTT file to extract word/sentence cue timestamps."""
    if not os.path.exists(srt_path):
        return []
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    cues = []
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) >= 3 and "-->" in lines[1]:
            time_part = lines[1]
            text = " ".join(lines[2:])
            try:
                start_str, end_str = time_part.split("-->")
                def parse_t(s):
                    s = s.strip().replace(",", ".")
                    parts = s.split(":")
                    if len(parts) == 3:
                        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    elif len(parts) == 2:
                        return float(parts[0]) * 60 + float(parts[1])
                    return float(s)
                cues.append({
                    "start": parse_t(start_str),
                    "end": parse_t(end_str),
                    "text": text
                })
            except Exception:
                pass
    return cues

def plan_scenes(topic, script=None):
    """Generate structured scene cards from topic or script."""
    if not script:
        # Generate default punchy 3-scene script
        script = f"Here is what you need to know about {topic}. First, it completely changes how you work. Second, it saves hours every single day. Start using it now!"
    
    sentences = [s.strip() for s in script.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if not sentences:
        sentences = [script]
        
    scenes = []
    colors = [
        {"bg": "#090d16", "accent": "#6366f1", "badge": "KEY INSIGHT"},
        {"bg": "#0f172a", "accent": "#38bdf8", "badge": "PRO ADVANTAGE"},
        {"bg": "#09090b", "accent": "#ec4899", "badge": "GAME CHANGER"},
        {"bg": "#030712", "accent": "#10b981", "badge": "TAKE ACTION"}
    ]
    
    for idx, sentence in enumerate(sentences):
        c = colors[idx % len(colors)]
        words = sentence.split()
        headline = " ".join(words[:4]) if len(words) > 4 else sentence
        body = " ".join(words[4:]) if len(words) > 4 else ""
        scenes.append({
            "index": idx + 1,
            "headline": headline,
            "body": body,
            "badge": c["badge"],
            "accent": c["accent"],
            "bg": c["bg"],
            "text": sentence
        })
        
    return script, scenes

def build_hyperframes_html(scenes, duration, aspect="portrait", audio_rel_path="voice.mp3"):
    """
    Generate deterministic HyperFrames HTML composition with GSAP timelines.
    Supports portrait (1080x1920) or landscape (1920x1080).
    """
    is_portrait = (aspect == "portrait")
    w = 1080 if is_portrait else 1920
    h = 1920 if is_portrait else 1080
    
    scene_dur = duration / max(1, len(scenes))
    
    scenes_html = []
    gsap_tweens = []
    
    for idx, sc in enumerate(scenes):
        st = idx * scene_dur
        ed = (idx + 1) * scene_dur
        scene_id = f"scene_{sc['index']}"
        initial_opacity = 1 if idx == 0 else 0
        z_idx = idx + 1
        
        scenes_html.append(f"""
        <!-- Scene {sc['index']} -->
        <div id="{scene_id}" class="scene" style="opacity: {initial_opacity}; z-index: {z_idx}; background: {sc['bg']};">
            <div class="card" style="border-color: {sc['accent']}33;">
                <div class="badge" style="background: {sc['accent']}22; color: {sc['accent']}; border: 1px solid {sc['accent']}55;">
                    {sc['badge']}
                </div>
                <h1 class="headline">{sc['headline']}</h1>
                {"<p class='body-text'>" + sc['body'] + "</p>" if sc['body'] else ""}
                <div class="progress-bar-bg">
                    <div id="bar_{sc['index']}" class="progress-bar-fill" style="background: {sc['accent']};"></div>
                </div>
            </div>
        </div>
        """)
        
        # GSAP animations
        if idx == 0:
            gsap_tweens.append(f"""
        // Scene 1 (Starts active)
        tl.fromTo("#{scene_id} .card", {{ y: 30, scale: 0.96 }}, {{ y: 0, scale: 1, duration: 0.45, ease: "back.out(1.4)" }}, 0);
        tl.fromTo("#bar_{sc['index']}", {{ width: "0%" }}, {{ width: "100%", duration: {scene_dur}, ease: "none" }}, 0);
            """)
        else:
            prev_scene_id = f"scene_{scenes[idx-1]['index']}"
            gsap_tweens.append(f"""
        // Scene {sc['index']} Transition In
        tl.fromTo("#{scene_id}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, ease: "power2.out" }}, {st});
        tl.fromTo("#{scene_id} .card", {{ y: 30, scale: 0.96 }}, {{ y: 0, scale: 1, duration: 0.45, ease: "back.out(1.4)" }}, {st});
        tl.fromTo("#bar_{sc['index']}", {{ width: "0%" }}, {{ width: "100%", duration: {scene_dur}, ease: "none" }}, {st});
        tl.set("#{prev_scene_id}", {{ opacity: 0 }}, {st + 0.3});
            """)

    gsap_code = "\n".join(gsap_tweens)
    all_scenes_markup = "\n".join(scenes_html)
    
    html = f"""<!doctype html>
<html lang="en" data-resolution="{aspect}">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            margin: 0; width: {w}px; height: {h}px; overflow: hidden;
            background: #000; font-family: Inter, system-ui, -apple-system, sans-serif;
        }}
        #root {{
            position: relative; width: 100%; height: 100%; overflow: hidden;
        }}
        .scene {{
            position: absolute; inset: 0; width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
            padding: 60px;
        }}
        .card {{
            width: 100%; max-width: {'880px' if is_portrait else '1200px'};
            padding: {'60px 48px' if is_portrait else '64px 80px'};
            background: rgba(18, 24, 38, 0.85);
            backdrop-filter: blur(20px);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 32px;
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7);
            display: flex; flex-direction: column; align-items: flex-start;
        }}
        .badge {{
            font-size: {'24px' if is_portrait else '20px'};
            font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
            padding: 8px 20px; border-radius: 999px; margin-bottom: 28px;
        }}
        .headline {{
            color: #ffffff;
            font-size: {'64px' if is_portrait else '56px'};
            font-weight: 800; line-height: 1.15; letter-spacing: -0.02em;
            margin-bottom: 24px;
        }}
        .body-text {{
            color: #94a3b8;
            font-size: {'36px' if is_portrait else '32px'};
            font-weight: 400; line-height: 1.4; margin-bottom: 36px;
        }}
        .progress-bar-bg {{
            width: 100%; height: 8px; background: rgba(255, 255, 255, 0.1);
            border-radius: 4px; overflow: hidden; margin-top: auto;
        }}
        .progress-bar-fill {{
            height: 100%; width: 0%; border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="{w}" data-height="{h}">
        <audio src="{audio_rel_path}" class="clip" data-start="0" data-duration="{duration}"></audio>
        {all_scenes_markup}
    </div>
    <script>
        const tl = gsap.timeline({{ paused: true }});
        window.__timelines = window.__timelines || {{}};
        window.__timelines["main"] = tl;
        
        {gsap_code}
        
        tl.seek(0);
    </script>
</body>
</html>
"""
    return html

def create_ai_video(topic, script=None, voice="en-US-ChristopherNeural", aspect="portrait", sound_genre="reels", out_dir=None):
    """
    Full End-to-End Generation:
    1. Plan script & scenes
    2. Generate Voiceover + VTT
    3. Build HyperFrames Composition
    4. Render Video via `npx hyperframes render`
    5. Take Snapshots for visual QA
    6. Run Smart Sound Design (BPT SFX + Ducking)
    """
    import re
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower()[:30]).strip('_') or "ai_video"
    project_dir = Path(out_dir or (PROJECTS_DIR / slug))
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Script & scenes
    final_script, scenes = plan_scenes(topic, script)
    
    # 2. Voiceover
    audio_path = project_dir / "voice.mp3"
    vtt_path = project_dir / "voice.vtt"
    generate_voiceover(final_script, voice=voice, out_audio=str(audio_path), out_vtt=str(vtt_path))
    duration = get_audio_duration(str(audio_path))
    
    # Pad duration slightly for clean ending
    total_duration = math.ceil(duration + 0.8)
    
    # 3. Write HyperFrames composition
    index_html = build_hyperframes_html(scenes, total_duration, aspect=aspect, audio_rel_path="voice.mp3")
    (project_dir / "index.html").write_text(index_html, encoding="utf-8")
    
    # Write metadata files for hyperframes CLI
    hyper_json = {
        "format": "hyperframes",
        "version": "1.0",
        "composition": "main",
        "fps": 30,
        "width": 1080 if aspect == "portrait" else 1920,
        "height": 1920 if aspect == "portrait" else 1080,
        "duration": total_duration
    }
    (project_dir / "hyperframes.json").write_text(json.dumps(hyper_json, indent=2), encoding="utf-8")
    
    package_json = {
        "name": slug,
        "private": True,
        "scripts": {
            "render": "hyperframes render -o out.mp4",
            "snapshot": "hyperframes snapshot"
        }
    }
    (project_dir / "package.json").write_text(json.dumps(package_json, indent=2), encoding="utf-8")
    
    # 4. Render with hyperframes
    raw_mp4 = project_dir / "raw_render.mp4"
    render_cmd = f'npx hyperframes render -o "{raw_mp4.name}"'
    code, out, err = run_cmd(render_cmd, cwd=str(project_dir))
    
    rendered_file = raw_mp4 if raw_mp4.exists() else (project_dir / "out.mp4")
    
    # 5. Snapshots for Agent & User visual review
    snapshot_cmd = "npx hyperframes snapshot"
    run_cmd(snapshot_cmd, cwd=str(project_dir))
    
    # Locate contact sheet if generated
    contact_sheet = None
    for p in project_dir.glob("**/*contact-sheet.jpg"):
        contact_sheet = str(p.resolve())
        break
        
    # 6. Apply Smart Sound Design (Whooshes on scene cuts, impacts, pops)
    final_video = str(project_dir / f"{slug}_master.mp4")
    sfx_stem = str(project_dir / f"{slug}_sfx_stem.wav")
    sound_data = None
    
    if design_soundtrack and rendered_file.exists():
        sound_data = design_soundtrack(
            str(rendered_file),
            genre=sound_genre,
            intensity="balanced",
            output_dir=str(project_dir)
        )
        if sound_data and sound_data.get("video_path") and os.path.exists(sound_data["video_path"]):
            final_video = sound_data["video_path"]
            sfx_stem = sound_data.get("sfx_stem_path")
    else:
        final_video = str(rendered_file)

    return {
        "status": "complete",
        "topic": topic,
        "duration": total_duration,
        "scenes_count": len(scenes),
        "video_path": final_video,
        "sfx_stem_path": sfx_stem if os.path.exists(sfx_stem) else None,
        "srt_path": str(vtt_path) if vtt_path.exists() else None,
        "contact_sheet": contact_sheet,
        "project_dir": str(project_dir.resolve()),
        "scenes": scenes,
        "sound_design": sound_data
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HyperFrames AI Video Pipeline")
    parser.add_argument("--topic", required=True, help="Topic or title for AI video")
    parser.add_argument("--script", default="", help="Optional custom script text")
    parser.add_argument("--voice", default="en-US-ChristopherNeural", help="TTS Voice")
    parser.add_argument("--aspect", default="portrait", choices=["portrait", "landscape"], help="Aspect ratio")
    parser.add_argument("--genre", default="reels", help="Sound design style genre")
    parser.add_argument("--output_dir", default="", help="Output project directory")
    
    args = parser.parse_args()
    res = create_ai_video(
        args.topic,
        script=args.script or None,
        voice=args.voice,
        aspect=args.aspect,
        sound_genre=args.genre,
        out_dir=args.output_dir or None
    )
    print(json.dumps(res, indent=2))
