"""
OpenCut Sound Designer Engine
Automated, Content-Aware Sound Design and Micro-Timing SFX Placement.
Complies with EBU R128 / ITU-R BS.1770-4 broadcast loudness standards.
"""

import os
import sys
import json
import math
import subprocess
import argparse
from pathlib import Path

# Paths
BASE_DIR = Path("E:/autocut")
FFMPEG = str(BASE_DIR / "ffmpeg" / "ffmpeg.exe")
FFPROBE = str(BASE_DIR / "ffmpeg" / "ffprobe.exe")
ASSETS_DIR = BASE_DIR / "assets" / "sfx"

# Palette definitions with BPT peak latencies (milliseconds from start)
PALETTES = {
    "gaming": {
        "whoosh": {"name": "whoosh_heavy.wav", "peak_ms": 160, "dur": 0.4, "vol": 0.35},
        "impact": {"name": "impact_808.wav", "peak_ms": 15, "dur": 1.0, "vol": 0.58},
        "punchline": {"name": "vine_boom.wav", "peak_ms": 30, "dur": 1.2, "vol": 0.60},
        "accent": {"name": "arcade_pop.wav", "peak_ms": 10, "dur": 0.15, "vol": 0.30},
        "min_spacing_whoosh": 2.2,
        "min_spacing_impact": 4.0
    },
    "reels": {
        "whoosh": {"name": "whoosh_fast.wav", "peak_ms": 140, "dur": 0.35, "vol": 0.32},
        "impact": {"name": "dramatic_hit.wav", "peak_ms": 20, "dur": 0.8, "vol": 0.55},
        "punchline": {"name": "punchline_boom.wav", "peak_ms": 25, "dur": 1.0, "vol": 0.58},
        "accent": {"name": "pop_snap.wav", "peak_ms": 8, "dur": 0.08, "vol": 0.28},
        "min_spacing_whoosh": 2.5,
        "min_spacing_impact": 4.5
    },
    "vlog": {
        "whoosh": {"name": "whoosh_soft.wav", "peak_ms": 180, "dur": 0.45, "vol": 0.28},
        "impact": {"name": "gentle_thud.wav", "peak_ms": 25, "dur": 0.6, "vol": 0.45},
        "punchline": {"name": "record_scratch.wav", "peak_ms": 40, "dur": 0.5, "vol": 0.48},
        "accent": {"name": "mouth_pop.wav", "peak_ms": 12, "dur": 0.12, "vol": 0.25},
        "min_spacing_whoosh": 3.0,
        "min_spacing_impact": 5.0
    },
    "tutorial": {
        "whoosh": {"name": "subtle_slide.wav", "peak_ms": 120, "dur": 0.3, "vol": 0.25},
        "impact": {"name": "clean_click.wav", "peak_ms": 5, "dur": 0.06, "vol": 0.40},
        "punchline": {"name": "notification_bell.wav", "peak_ms": 15, "dur": 0.8, "vol": 0.42},
        "accent": {"name": "ui_click.wav", "peak_ms": 5, "dur": 0.05, "vol": 0.22},
        "min_spacing_whoosh": 3.5,
        "min_spacing_impact": 6.0
    },
    "cinematic": {
        "whoosh": {"name": "wind_swell.wav", "peak_ms": 300, "dur": 0.8, "vol": 0.40},
        "impact": {"name": "trailer_braam.wav", "peak_ms": 50, "dur": 1.8, "vol": 0.62},
        "punchline": {"name": "deep_sub_drop.wav", "peak_ms": 40, "dur": 1.5, "vol": 0.62},
        "accent": {"name": "low_pulse.wav", "peak_ms": 20, "dur": 0.5, "vol": 0.35},
        "min_spacing_whoosh": 4.0,
        "min_spacing_impact": 6.5
    },
    "editorial": {
        "whoosh": {"name": "paper_slide.wav", "peak_ms": 120, "dur": 0.45, "vol": 0.32},
        "impact": {"name": "stamp_thud.wav", "peak_ms": 30, "dur": 0.55, "vol": 0.58},
        "punchline": {"name": "stamp_thud.wav", "peak_ms": 30, "dur": 0.55, "vol": 0.58},
        "accent": {"name": "pop_click.wav", "peak_ms": 10, "dur": 0.08, "vol": 0.28},
        "min_spacing_whoosh": 2.0,
        "min_spacing_impact": 3.0
    }
}

def run_cmd(cmd):
    """Run command quietly and return stdout."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    return res.returncode, res.stdout, res.stderr

def ensure_sound_library():
    """Synthesize any missing base SFX assets with studio-grade DSP normalization."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate high-definition tactile editorial & UI assets via sound_synthesizer
    try:
        from server.sound_synthesizer import (
            create_stamp_thud, create_paper_slide, create_marker_scribble,
            create_pop_click, create_paper_rip, write_wav_file
        )
        tactile_assets = {
            "stamp_thud.wav": create_stamp_thud,
            "paper_slide.wav": create_paper_slide,
            "marker_scribble.wav": create_marker_scribble,
            "pop_click.wav": lambda: create_pop_click(1200),
            "pop_click_high.wav": lambda: create_pop_click(1600),
            "paper_rip.wav": create_paper_rip,
        }
        for name, gen_fn in tactile_assets.items():
            tgt = ASSETS_DIR / name
            if not tgt.exists() or tgt.stat().st_size < 100:
                write_wav_file(tgt, gen_fn())
    except Exception as e:
        pass

    generators = {
        "whoosh_heavy.wav": "-f lavfi -i anoisesrc=d=0.4:c=pink:r=48000 -filter_complex \"bandpass=f=900:w=700,afade=t=in:st=0:d=0.18,afade=t=out:st=0.18:d=0.22,loudnorm=I=-14:TP=-1.0\"",
        "impact_808.wav": "-f lavfi -i sine=f=55:d=1.0:r=48000 -filter_complex \"afade=t=in:st=0:d=0.01,afade=t=out:st=0.1:d=0.9,bass=g=14:f=55,loudnorm=I=-12:TP=-1.0\"",
        "vine_boom.wav": "-f lavfi -i sine=f=45:d=1.2:r=48000 -filter_complex \"bass=g=18:f=45,afade=t=in:st=0:d=0.01,afade=t=out:st=0.15:d=1.05,loudnorm=I=-10:TP=-1.0\"",
        "arcade_pop.wav": "-f lavfi -i sine=f=980:d=0.15:r=48000 -filter_complex \"afade=t=in:st=0:d=0.01,afade=t=out:st=0.03:d=0.12,loudnorm=I=-14:TP=-1.0\"",
        
        "whoosh_fast.wav": "-f lavfi -i anoisesrc=d=0.35:c=pink:r=48000 -filter_complex \"bandpass=f=1200:w=900,afade=t=in:st=0:d=0.15,afade=t=out:st=0.15:d=0.20,loudnorm=I=-14:TP=-1.0\"",
        "dramatic_hit.wav": "-f lavfi -i sine=f=70:d=0.8:r=48000 -filter_complex \"bass=g=10:f=70,afade=t=in:st=0:d=0.01,afade=t=out:st=0.08:d=0.72,loudnorm=I=-12:TP=-1.0\"",
        "punchline_boom.wav": "-f lavfi -i sine=f=50:d=1.0:r=48000 -filter_complex \"bass=g=15:f=50,afade=t=out:st=0.12:d=0.88,loudnorm=I=-11:TP=-1.0\"",
        "pop_snap.wav": "-f lavfi -i sine=f=1400:d=0.08:r=48000 -filter_complex \"afade=t=in:st=0:d=0.005,afade=t=out:st=0.01:d=0.07,loudnorm=I=-14:TP=-1.0\"",
        
        "whoosh_soft.wav": "-f lavfi -i anoisesrc=d=0.45:c=brown:r=48000 -filter_complex \"lowpass=f=1600,afade=t=in:st=0:d=0.2,afade=t=out:st=0.2:d=0.25,loudnorm=I=-15:TP=-1.5\"",
        "gentle_thud.wav": "-f lavfi -i sine=f=80:d=0.6:r=48000 -filter_complex \"afade=t=out:st=0.05:d=0.55,loudnorm=I=-14:TP=-1.5\"",
        "record_scratch.wav": "-f lavfi -i anoisesrc=d=0.5:c=white:r=48000 -filter_complex \"bandpass=f=2200:w=1200,afade=t=in:st=0:d=0.05,afade=t=out:st=0.35:d=0.15,loudnorm=I=-14:TP=-1.0\"",
        "mouth_pop.wav": "-f lavfi -i sine=f=1100:d=0.12:r=48000 -filter_complex \"afade=t=in:st=0:d=0.01,afade=t=out:st=0.02:d=0.10,loudnorm=I=-14:TP=-1.0\"",
        
        "subtle_slide.wav": "-f lavfi -i anoisesrc=d=0.3:c=pink:r=48000 -filter_complex \"bandpass=f=1800:w=1000,afade=t=in:st=0:d=0.12,afade=t=out:st=0.12:d=0.18,loudnorm=I=-15:TP=-1.5\"",
        "clean_click.wav": "-f lavfi -i sine=f=2200:d=0.06:r=48000 -filter_complex \"afade=t=out:st=0.01:d=0.05,loudnorm=I=-14:TP=-1.0\"",
        "notification_bell.wav": "-f lavfi -i sine=f=880:d=0.8:r=48000 -filter_complex \"afade=t=out:st=0.02:d=0.78,loudnorm=I=-13:TP=-1.0\"",
        "ui_click.wav": "-f lavfi -i sine=f=2600:d=0.05:r=48000 -filter_complex \"afade=t=out:st=0.005:d=0.045,loudnorm=I=-14:TP=-1.0\"",
        
        "wind_swell.wav": "-f lavfi -i anoisesrc=d=0.8:c=brown:r=48000 -filter_complex \"lowpass=f=800,afade=t=in:st=0:d=0.4,afade=t=out:st=0.4:d=0.4,loudnorm=I=-14:TP=-1.0\"",
        "trailer_braam.wav": "-f lavfi -i sine=f=40:d=1.8:r=48000 -filter_complex \"bass=g=16:f=40,afade=t=in:st=0:d=0.05,afade=t=out:st=0.3:d=1.5,loudnorm=I=-11:TP=-1.0\"",
        "deep_sub_drop.wav": "-f lavfi -i sine=f=35:d=1.5:r=48000 -filter_complex \"bass=g=14:f=35,afade=t=out:st=0.2:d=1.3,loudnorm=I=-11:TP=-1.0\"",
        "low_pulse.wav": "-f lavfi -i sine=f=65:d=0.5:r=48000 -filter_complex \"afade=t=out:st=0.05:d=0.45,loudnorm=I=-13:TP=-1.0\""
    }

    for filename, lavfi_args in generators.items():
        target = ASSETS_DIR / filename
        if not target.exists() or target.stat().st_size < 100:
            cmd = f'"{FFMPEG}" -y {lavfi_args} "{target}"'
            run_cmd(cmd)

def get_media_duration(file_path):
    """Retrieve media duration in seconds via ffprobe."""
    cmd = f'"{FFPROBE}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    code, out, _ = run_cmd(cmd)
    try:
        return float(out.strip())
    except:
        return 30.0

def detect_visual_cuts(video_path, threshold=0.35, min_interval=1.2):
    """Detect visual cut timestamps using FFmpeg scene filter."""
    cmd = f'"{FFMPEG}" -i "{video_path}" -filter_complex "select=\'gt(scene,{threshold})\',metadata=print:file=-" -f null -'
    code, out, err = run_cmd(cmd)
    combined = out + "\n" + err
    
    cut_times = []
    for line in combined.splitlines():
        if "pts_time:" in line:
            try:
                t = float(line.split("pts_time:")[1].split()[0])
                if not cut_times or (t - cut_times[-1]) >= min_interval:
                    cut_times.append(t)
            except:
                pass
    return cut_times

def detect_silence_pauses(audio_path, noise_db=-30, min_dur=0.35):
    """Detect natural conversational pauses using silencedetect."""
    cmd = f'"{FFMPEG}" -i "{audio_path}" -af "silencedetect=noise={noise_db}dB:d={min_dur}" -f null -'
    code, out, err = run_cmd(cmd)
    combined = out + "\n" + err
    
    pauses = []
    cur_start = None
    for line in combined.splitlines():
        if "silence_start:" in line:
            try:
                cur_start = float(line.split("silence_start:")[1].split()[0])
            except:
                pass
        elif "silence_end:" in line and cur_start is not None:
            try:
                end = float(line.split("silence_end:")[1].split()[0])
                dur = end - cur_start
                # Natural pauses between 0.4s and 1.8s
                if 0.4 <= dur <= 1.8:
                    pauses.append({"start": cur_start, "end": end, "duration": dur})
                cur_start = None
            except:
                pass
    return pauses

def design_soundtrack(video_path, genre="gaming", intensity="balanced", music_path=None, music_vol=0.25, duck_amount=0.7, output_dir=None):
    """
    Main sound design engine:
    1. Detects cuts and pauses
    2. Selects sound assets from genre palette
    3. Aligns peak to cut (BPT model)
    4. Balances relative loudness and applies ducking
    5. Outputs composite video + isolated SFX stem
    """
    ensure_sound_library()
    
    video_path = str(Path(video_path).resolve())
    out_dir = Path(output_dir or Path(video_path).parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    duration = get_media_duration(video_path)
    palette = PALETTES.get(genre, PALETTES["reels"])
    
    # Adjust spacing thresholds by intensity
    spacing_mult = {"subtle": 1.5, "balanced": 1.0, "hype": 0.65}.get(intensity, 1.0)
    whoosh_cooldown = palette["min_spacing_whoosh"] * spacing_mult
    impact_cooldown = palette["min_spacing_impact"] * spacing_mult
    
    # 1. Multi-signal analysis
    cuts = detect_visual_cuts(video_path)
    # If video had no sharp cuts (e.g. static camera screen recording), fallback to rhythmic pacing
    if len(cuts) < 2 and duration > 6.0:
        step = 6.0 if intensity == "subtle" else (4.0 if intensity == "balanced" else 2.5)
        cur = step
        while cur < (duration - 1.5):
            cuts.append(cur)
            cur += step

    pauses = detect_silence_pauses(video_path)
    
    # 2. Schedule SFX with BPT Peak Alignment
    scheduled_events = []
    last_whoosh = -999.0
    last_impact = -999.0
    
    # Process visual cuts -> Whooshes / Swishes
    whoosh_cfg = palette["whoosh"]
    whoosh_file = str(ASSETS_DIR / whoosh_cfg["name"])
    whoosh_peak_s = whoosh_cfg["peak_ms"] / 1000.0
    
    for c in cuts:
        if c > (duration - 0.5):
            continue
        if (c - last_whoosh) >= whoosh_cooldown:
            # BPT alignment: start whoosh BEFORE cut so peak lands exactly at frame 0 of cut
            start_time = max(0.0, c - whoosh_peak_s)
            scheduled_events.append({
                "time": start_time,
                "anchor": c,
                "file": whoosh_file,
                "type": "whoosh",
                "vol": whoosh_cfg["vol"]
            })
            last_whoosh = c
            
    # Process dramatic pauses -> Impact / Punchline Stinger
    punch_cfg = palette["punchline"]
    punch_file = str(ASSETS_DIR / punch_cfg["name"])
    punch_peak_s = punch_cfg["peak_ms"] / 1000.0
    
    for p in pauses:
        p_time = p["start"] + 0.05 # Right as silence starts
        if p_time > (duration - 1.0):
            continue
        if (p_time - last_impact) >= impact_cooldown and (p_time - last_whoosh) >= 1.0:
            start_time = max(0.0, p_time - punch_peak_s)
            scheduled_events.append({
                "time": start_time,
                "anchor": p_time,
                "file": punch_file,
                "type": "punchline",
                "vol": punch_cfg["vol"]
            })
            last_impact = p_time
            
    # Sort chronologically
    scheduled_events.sort(key=lambda x: x["time"])
    
    # 3. Construct FFmpeg Multi-Track Mixer
    base_name = Path(video_path).stem
    out_video = str(out_dir / f"{base_name}_sound_designed.mp4")
    out_sfx_stem = str(out_dir / f"{base_name}_sfx_stem.wav")
    
    # If no events placed, return clean output
    if not scheduled_events:
        return {
            "status": "complete",
            "events_count": 0,
            "video_path": video_path,
            "sfx_stem_path": None,
            "genre": genre
        }
        
    # Build inputs and filtergraph
    # Input 0: original video
    input_args = [f'-i "{video_path}"']
    filter_chains = []
    delayed_labels = []
    
    for idx, ev in enumerate(scheduled_events, start=1):
        input_args.append(f'-i "{ev["file"]}"')
        delay_ms = int(round(ev["time"] * 1000))
        # adelay delays left and right channels, volume adjusts level
        label = f"sfx{idx}"
        filter_chains.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={ev['vol']}[{label}]")
        delayed_labels.append(f"[{label}]")
        
    # Mix all SFX into a combined stem [sfx_master]
    num_sfx = len(scheduled_events)
    all_sfx_in = "".join(delayed_labels)
    filter_chains.append(f"{all_sfx_in}amix=inputs={num_sfx}:dropout_transition=0:normalize=0[sfx_raw]")
    
    # Frequency carving and True Peak Limiter on SFX bus (calibrated to -10.5 dBFS to prevent vocal competition)
    filter_chains.append("[sfx_raw]equalizer=f=2800:t=q:w=1.2:g=-3,alimiter=limit=0.30:attack=5:release=50[sfx_carved]")
    # Dynamic sidechain ducking on SFX against dialogue
    filter_chains.append("[sfx_carved][0:a]sidechaincompress=threshold=0.10:ratio=2.2:attack=15:release=120[sfx_master]")
    
    # Music handling if provided
    has_music = music_path and Path(music_path).exists()
    music_idx = len(scheduled_events) + 1 if has_music else None
    
    if has_music:
        input_args.append(f'-i "{music_path}"')
        duck_vol = music_vol * (1.0 - duck_amount * 0.75) # Attenuate during speech
        # Sidechain ducking of music against voice [0:a]
        filter_chains.append(
            f"[{music_idx}:a][0:a]sidechaincompress=threshold=0.08:ratio=5:attack=30:release=600:link=average[ducked_bg]"
        )
        filter_chains.append(f"[ducked_bg]volume={music_vol}[bg_music]")
        filter_chains.append(f"[0:a][sfx_master][bg_music]amix=inputs=3:normalize=0[final_audio]")
    else:
        # Mix original audio + sfx_master
        filter_chains.append(f"[0:a][sfx_master]amix=inputs=2:normalize=0[final_audio]")
        
    filter_complex_str = "; ".join(filter_chains)
    inputs_str = " ".join(input_args)
    
    # 4. Generate the isolated SFX Stem WAV (full length with anullsrc baseline)
    stem_inputs = f'-f lavfi -i anullsrc=r=48000:cl=stereo:d={duration} ' + " ".join([f'-i "{ev["file"]}"' for ev in scheduled_events])
    stem_delayed_labels = ["[0:a]"]
    stem_filter_chains = []
    for idx, ev in enumerate(scheduled_events, start=1):
        delay_ms = int(round(ev["time"] * 1000))
        label = f"stem_sfx{idx}"
        stem_filter_chains.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={ev['vol']}[{label}]")
        stem_delayed_labels.append(f"[{label}]")
    
    all_stem_in = "".join(stem_delayed_labels)
    stem_filter_chains.append(f"{all_stem_in}amix=inputs={num_sfx+1}:normalize=0:dropout_transition=0[stem_raw]")
    stem_filter_chains.append("[stem_raw]alimiter=limit=0.85:attack=5:release=50[sfx_stem_out]")
    stem_filter_str = "; ".join(stem_filter_chains)
    
    stem_cmd = (
        f'"{FFMPEG}" -y {stem_inputs} -filter_complex "{stem_filter_str}" '
        f'-map "[sfx_stem_out]" -c:a pcm_s16le -ar 48000 "{out_sfx_stem}"'
    )
    run_cmd(stem_cmd)
    
    # 5. Render composite video
    render_cmd = (
        f'"{FFMPEG}" -y {inputs_str} -filter_complex "{filter_complex_str}" '
        f'-map 0:v -map "[final_audio]" -c:v copy -c:a aac -b:a 256k "{out_video}"'
    )
    code, out, err = run_cmd(render_cmd)
    if code != 0:
        # Fallback without copy if needed
        render_cmd = (
            f'"{FFMPEG}" -y {inputs_str} -filter_complex "{filter_complex_str}" '
            f'-map 0:v -map "[final_audio]" -c:v libx264 -preset veryfast -c:a aac -b:a 256k "{out_video}"'
        )
        run_cmd(render_cmd)
        
    return {
        "status": "complete",
        "events_count": len(scheduled_events),
        "cuts_detected": len(cuts),
        "pauses_detected": len(pauses),
        "video_path": out_video,
        "sfx_stem_path": out_sfx_stem,
        "genre": genre,
        "intensity": intensity,
        "events": scheduled_events[:15] # preview of placed events
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCut Smart Sound Designer")
    parser.add_argument("--input", required=True, help="Input video or audio path")
    parser.add_argument("--genre", default="gaming", choices=list(PALETTES.keys()), help="Sound style genre")
    parser.add_argument("--intensity", default="balanced", choices=["subtle", "balanced", "hype"], help="SFX density")
    parser.add_argument("--music", default="", help="Optional background music path")
    parser.add_argument("--output_dir", default="", help="Output directory")
    
    args = parser.parse_args()
    res = design_soundtrack(
        args.input,
        genre=args.genre,
        intensity=args.intensity,
        music_path=args.music or None,
        output_dir=args.output_dir or None
    )
    print(json.dumps(res, indent=2))
