"""
OpenCut Selective Keyword Cue & Animated Callout Overlay Engine
==============================================================
Transcribes video audio with word-level precision, spots user-designated
target keywords/phrases, and generates:
1. Precision ASS animated kinetic captions with famous YouTuber styles (MrBeast, Hormozi, etc.).
2. Clean SRT subtitles for the spotted words.
3. Optional synchronized sound effect cue audio stem (track A2/A3).
4. Direct Adobe Premiere Pro timeline placement configuration.
"""

import os
import sys
import json
import time
import math
import struct
import wave
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path("E:/autocut")
FFMPEG = str(BASE_DIR / "ffmpeg" / "ffmpeg.exe")
FFPROBE = str(BASE_DIR / "ffmpeg" / "ffprobe.exe")
WORK_DIR = BASE_DIR / "work"
SFX_DIR = BASE_DIR / "assets" / "sfx"

# Famous YouTuber & Creator Visual Style Definitions
YOUTUBER_STYLES = {
    "mrbeast": {
        "name": "MrBeast Bold Punch",
        "font": "Impact",
        "primary_color": "&H0000EEFF&",    # Bright Yellow (#FFEE00)
        "secondary_color": "&H00F2FE00&",  # Cyan highlight (#00F2FE)
        "outline_color": "&H00000000&",    # Pure Black
        "outline_width": 4.5,
        "shadow_depth": 3.0,
        "bold": -1,
        "anim_tags": r"{\fscx140\fscy140\t(0,100,\fscx100\fscy100)}" # Overshoot pop
    },
    "alex_hormozi": {
        "name": "Alex Hormozi Viral",
        "font": "Montserrat",
        "primary_color": "&H00FFFFFF&",    # Crisp White
        "secondary_color": "&H0015CCFA&",  # Warm Yellow (#FACC15)
        "outline_color": "&H000B0D14&",    # Deep Charcoal
        "outline_width": 3.8,
        "shadow_depth": 2.0,
        "bold": -1,
        "anim_tags": r"{\fscx125\fscy125\t(0,80,\fscx100\fscy100)}"
    },
    "ali_abdaal": {
        "name": "Ali Abdaal Aesthetic",
        "font": "Inter",
        "primary_color": "&H00F8FAFC&",    # Off-white
        "secondary_color": "&H00F8BD38&",  # Soft Sky Blue
        "outline_color": "&H80000000&",    # Translucent
        "outline_width": 1.5,
        "shadow_depth": 1.0,
        "bold": -1,
        "anim_tags": r"{\fad(80,80)}"      # Smooth subtle fade
    },
    "iman_gadzhi": {
        "name": "Iman Gadzhi Luxury",
        "font": "Cinzel",
        "primary_color": "&H000BB5F5&",    # Luxury Gold (#F5B50B)
        "secondary_color": "&H00FFFFFF&",  # White
        "outline_color": "&H00000000&",    # Black
        "outline_width": 2.5,
        "shadow_depth": 3.0,
        "bold": -1,
        "anim_tags": r"{\blur3\fscx110\fscy110\t(0,120,\fscx100\fscy100)}"
    },
    "neon_glow": {
        "name": "Cyberpunk Neon Glow",
        "font": "Arial",
        "primary_color": "&H0022D3EE&",    # Vibrant Cyan
        "secondary_color": "&H00FF00FF&",  # Magenta
        "outline_color": "&H00000000&",
        "outline_width": 3.0,
        "shadow_depth": 0.0,
        "bold": -1,
        "anim_tags": r"{\blur8\3c&H0022D3EE&\t(0,100,\blur2)}"
    },
    "comic_punch": {
        "name": "Comic Impact",
        "font": "Impact",
        "primary_color": "&H000000FF&",    # Vivid Red
        "secondary_color": "&H0000EEFF&",  # Yellow
        "outline_color": "&H00FFFFFF&",    # White border
        "outline_width": 4.0,
        "shadow_depth": 3.5,
        "bold": -1,
        "anim_tags": r"{\fscx150\fscy150\t(0,90,\fscx95\fscy95)\t(90,140,\fscx100\fscy100)}"
    },
    "minimal_tag": {
        "name": "Minimalist Tag",
        "font": "Arial",
        "primary_color": "&H00FFFFFF&",
        "secondary_color": "&H0094A3B8&",
        "outline_color": "&H00000000&",
        "outline_width": 2.0,
        "shadow_depth": 1.0,
        "bold": 0,
        "anim_tags": r"{\fad(60,60)}"
    }
}


def run_cmd(cmd: str) -> Tuple[int, str, str]:
    """Execute shell command."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    return res.returncode, res.stdout, res.stderr


def get_video_duration(filepath: str) -> float:
    """Get video duration using ffprobe."""
    cmd = f'"{FFPROBE}" -v error -show_entries format=duration -of json "{filepath}"'
    code, out, _ = run_cmd(cmd)
    if code == 0 and out.strip():
        try:
            return float(json.loads(out).get("format", {}).get("duration", 0.0))
        except Exception:
            pass
    return 10.0


def extract_audio_for_transcription(video_path: str, wav_path: str) -> bool:
    """Extract audio to 16kHz mono WAV for Whisper."""
    cmd = f'"{FFMPEG}" -y -i "{video_path}" -vn -ar 16000 -ac 1 -c:a pcm_s16le "{wav_path}"'
    code, _, _ = run_cmd(cmd)
    return code == 0 and os.path.exists(wav_path)


def sec_to_srt(s: float) -> str:
    hrs = int(s // 3600)
    mins = int((s % 3600) // 60)
    secs = int(s % 60)
    mils = int((s - int(s)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{mils:03d}"


def sec_to_ass(s: float) -> str:
    hrs = int(s // 3600)
    mins = int((s % 3600) // 60)
    secs = int(s % 60)
    cs = int((s - int(s)) * 100)
    return f"{hrs:01d}:{mins:02d}:{secs:02d}.{cs:02d}"


def generate_keyword_sfx_stem(
    cue_times: List[float],
    total_duration: float,
    out_wav_path: str,
    sfx_type: str = "pop"
) -> bool:
    """
    Synthesizes an audio stem WAV file containing a crisp sound effect
    at every detected keyword occurrence.
    """
    sr = 44100
    total_samples = int(total_duration * sr)
    if total_samples <= 0:
        return False

    buffer = [0.0] * total_samples

    # Load or synthesize cue SFX
    sfx_file = SFX_DIR / f"{sfx_type}.wav"
    if not sfx_file.exists():
        sfx_file = SFX_DIR / "pop_click.wav"
    if not sfx_file.exists():
        sfx_file = SFX_DIR / "bell_ding.wav"

    sfx_samples = []
    if sfx_file.exists():
        try:
            with wave.open(str(sfx_file), "rb") as w:
                nch = w.getnchannels()
                sw = w.getsampwidth()
                fr = w.getframerate()
                frames = w.readframes(w.getnframes())
                if sw == 2:
                    for i in range(0, len(frames), 2 * nch):
                        val = struct.unpack("<h", frames[i:i+2])[0]
                        sfx_samples.append(val / 32768.0)
        except Exception:
            pass

    # Fallback synthesizer if no WAV
    if not sfx_samples:
        pop_len = int(sr * 0.12)
        for i in range(pop_len):
            t = i / sr
            env = math.exp(-60.0 * t)
            sfx_samples.append(math.sin(2.0 * math.pi * 1800.0 * t) * env * 0.8)

    # Place SFX samples at each cue timestamp
    for cue_t in cue_times:
        start_idx = int(cue_t * sr)
        for j, samp in enumerate(sfx_samples):
            pos = start_idx + j
            if pos < total_samples:
                buffer[pos] = max(-1.0, min(1.0, buffer[pos] + samp * 0.75))

    # Write WAV
    try:
        with wave.open(out_wav_path, "wb") as out_w:
            out_w.setnchannels(1)
            out_w.setsampwidth(2)
            out_w.setframerate(sr)
            raw = bytearray()
            for s in buffer:
                int_s = int(max(-1.0, min(1.0, s)) * 32767.0)
                raw.extend(struct.pack("<h", int_s))
            out_w.writeframes(raw)
        return True
    except Exception as e:
        sys.stderr.write(f"SFX stem error: {e}\n")
        return False


def spot_keywords_and_generate_cues(
    filepath: str,
    target_words: List[str],
    output_dir: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entry point for Selective Keyword Spotter & Caption Callout Engine:
    1. Transcribes audio with word-level timestamps.
    2. Spots all occurrences of target_words.
    3. Generates stylized ASS/SRT caption files specifically for those keywords.
    4. Generates synchronized SFX cues.
    5. Returns timeline configuration for Adobe Premiere Pro.
    """
    options = options or {}
    input_p = Path(filepath)
    if not input_p.exists():
        raise FileNotFoundError(f"Source video not found: {filepath}")

    base_name = input_p.stem
    ts = int(time.time())
    out_dir = Path(output_dir) if output_dir and os.path.exists(output_dir) else WORK_DIR / f"{base_name}_cues_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    total_dur = get_video_duration(str(input_p))

    # Normalize target words
    cleaned_targets = []
    for tw in target_words:
        if isinstance(tw, str):
            for part in tw.replace(",", " ").split():
                clean_p = part.strip().lower()
                if clean_p and clean_p not in cleaned_targets:
                    cleaned_targets.append(clean_p)

    if not cleaned_targets:
        cleaned_targets = ["subscribe", "like", "money", "secret"]

    # 1. Transcribe audio to extract words
    temp_wav = str(out_dir / f"{base_name}_temp16k.wav")
    extract_audio_for_transcription(str(input_p), temp_wav)

    words_list = []
    lang = options.get("language") or "auto"
    model_size = options.get("model") or "base"

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang_arg = None if (not lang or lang == "auto") else lang
        segments, info = model.transcribe(temp_wav, language=lang_arg, beam_size=2, word_timestamps=True)
        for seg in segments:
            if hasattr(seg, "words") and seg.words:
                for w in seg.words:
                    clean_w = w.word.strip().lower().strip('.,!?":;()[]{}')
                    words_list.append({
                        "word": w.word.strip(),
                        "clean": clean_w,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2)
                    })
    except Exception as e:
        sys.stderr.write(f"[Keyword Spotter] Whisper transcription notice: {e}\n")

    # Clean up temp 16k wav
    if os.path.exists(temp_wav):
        try: os.remove(temp_wav)
        except Exception: pass

    # 2. Match Target Words
    matches = []
    cue_times = []
    target_set = set(cleaned_targets)

    for item in words_list:
        clean_w = item["clean"]
        if clean_w in target_set:
            st = max(0.0, item["start"] - 0.05)
            # Duration: at least 0.65s for readability
            dur = max(0.65, item["end"] - item["start"] + 0.35)
            et = min(total_dur, st + dur)

            match_entry = {
                "word": item["word"],
                "target": clean_w,
                "start": round(st, 2),
                "end": round(et, 2),
                "duration": round(et - st, 2),
                "timestamp_str": f"{int(st//60)}:{int(st%60):02d}.{int((st%1)*10):01d}"
            }
            matches.append(match_entry)
            cue_times.append(st)

    # 3. Visual Styling & Configuration
    style_key = options.get("style", "mrbeast")
    st_cfg = YOUTUBER_STYLES.get(style_key, YOUTUBER_STYLES["mrbeast"])
    font_size = int(options.get("font_size", 54))
    position = options.get("position", "center") # "center", "lower_third", "top"

    # Alignment in ASS: 2 = bottom-center, 5 = middle-center, 8 = top-center
    alignment = 5 if position == "center" else (8 if position == "top" else 2)
    margin_v = 80 if position == "lower_third" else (50 if position == "top" else 0)

    anim_effect = options.get("animation", "pop")
    anim_tag = st_cfg.get("anim_tags", "")
    if anim_effect == "bounce":
        anim_tag = r"{\fscx80\fscy80\t(0,90,\fscx130\fscy130)\t(90,160,\fscx100\fscy100)}"
    elif anim_effect == "slide_up":
        anim_tag = r"{\fscx100\fscy100\fad(80,80)}"

    # 4. Generate ASS and SRT Files
    out_ass_path = str(out_dir / f"{base_name}_keyword_cues.ass")
    out_srt_path = str(out_dir / f"{base_name}_keyword_cues.srt")

    srt_lines = []
    ass_dialogues = []

    for i, m in enumerate(matches, 1):
        st = m["start"]
        et = m["end"]
        word_text = m["word"].upper()

        # SRT entry
        srt_lines.append(f"{i}\n{sec_to_srt(st)} --> {sec_to_srt(et)}\n{word_text}\n")

        # ASS entry with active animation tag
        styled_text = f"{anim_tag}{word_text}"
        ass_dialogues.append(
            f"Dialogue: 0,{sec_to_ass(st)},{sec_to_ass(et)},KeywordCue,,0,0,0,,{styled_text}"
        )

    # Write SRT
    with open(out_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # Write ASS with complete high-resolution styling
    ass_content = f"""[Script Info]
Title: OpenCut Keyword Cues
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KeywordCue,{st_cfg['font']},{font_size},{st_cfg['primary_color']},{st_cfg['secondary_color']},{st_cfg['outline_color']},&H80000000,{st_cfg['bold']},0,0,0,100,100,1,0,1,{st_cfg['outline_width']},{st_cfg['shadow_depth']},{alignment},30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ass_dialogues) + "\n"

    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    # 5. Optional SFX Cue Stem Generation
    add_sound_cue = options.get("add_sound_cue", True)
    sfx_stem_path = None
    if add_sound_cue and cue_times:
        sfx_type = options.get("sfx_type", "pop_click")
        sfx_stem_path = str(out_dir / f"{base_name}_keyword_sfx.wav")
        generate_keyword_sfx_stem(cue_times, total_dur, sfx_stem_path, sfx_type=sfx_type)

    target_track = options.get("target_track", "v4")

    return {
        "status": "success",
        "detected_count": len(matches),
        "matches": matches,
        "target_words": cleaned_targets,
        "style": style_key,
        "style_name": st_cfg["name"],
        "target_track": target_track,
        "ass_path": out_ass_path if matches else None,
        "srt_path": out_srt_path if matches else None,
        "sfx_stem_path": sfx_stem_path if (sfx_stem_path and os.path.exists(sfx_stem_path)) else None,
        "video_duration": round(total_dur, 2)
    }
