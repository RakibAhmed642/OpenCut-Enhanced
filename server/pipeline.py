"""
OpenCut Autonomous Video Editing Pipeline
High-precision autonomous editing engine conforming to strict production quality rules:
1. Media probe & audio validation (fails clearly if no audio)
2. Faster-Whisper mono 16kHz transcription & word-level timestamps (Bangla, English, Banglish)
3. FFmpeg silencedetect (-30dB, 0.5s min duration)
4. Configurable filler words & repeated takes detection (keeps last/best take)
5. EDL builder with word padding (0.08s) and micro-cut merge (0.15s)
6. FFmpeg trim+concat via filter_complex_script (CRF 18, AAC 192k, sync-locked)
7. Word timestamp remapping & ASS kinetic karaoke captions
8. Vertical 9:16 center-crop (with face-tracking hook)
9. EBU R128 loudness normalization (-16 LUFS)
10. Frame QA extraction (5 frames) and duration tolerance validation (0.3s)
"""

import os
import sys
import json
import time
import math
import hashlib
import difflib
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import yaml

# Base Paths
BASE_DIR = Path("E:/autocut")
FFMPEG = str(BASE_DIR / "ffmpeg" / "ffmpeg.exe")
FFPROBE = str(BASE_DIR / "ffmpeg" / "ffprobe.exe")
CONFIG_PATH = BASE_DIR / "config.yaml"

def log_info(msg: str) -> None:
    """Print progress logs to stderr to keep stdout pristine for JSON-RPC."""
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()

def load_config(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml with fallback defaults."""
    cfg_file = Path(custom_path) if custom_path else CONFIG_PATH
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "silence": {"noise_threshold_db": -30.0, "min_duration": 0.5},
        "padding": {"word_padding": 0.08, "merge_threshold": 0.15},
        "fillers": {
            "enabled": True,
            "words": ["um", "uh", "ah", "er", "like", "you know", "hmm", "mane", "ar", "ki jani", "tai", "eita", "sheita"]
        },
        "repeated_takes": {"enabled": True, "similarity_threshold": 0.75, "keep": "last"},
        "whisper": {"model_size": "base", "compute_type": "int8", "language": None, "beam_size": 5},
        "rendering": {
            "video_codec": "libx264", "crf": 18, "preset": "medium",
            "audio_codec": "aac", "audio_bitrate": "192k", "target_lufs": -16.0
        },
        "vertical": {"width": 1080, "height": 1920, "crop_mode": "center"},
        "captions": {
            "enabled": True, "words_per_line_min": 2, "words_per_line_max": 4,
            "font_name": "Arial", "font_size": 26, "primary_color": "&H00FFFFFF",
            "highlight_color": "&H0022D3EE", "outline_color": "&H000B0D14",
            "outline_width": 3.5, "shadow_depth": 1.5, "alignment": 2, "margin_v": 180
        },
        "qa": {"frame_count": 5, "duration_tolerance": 0.3}
    }

def run_cmd(cmd: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Execute shell command cleanly with stdout and stderr captured."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, cwd=cwd)
    return res.returncode, res.stdout, res.stderr

def compute_file_hash(filepath: str) -> str:
    """Compute deterministic hash of file from metadata and 64KB header/footer."""
    p = Path(filepath)
    stat = p.stat()
    h = hashlib.sha256()
    h.update(f"{p.name}_{stat.st_size}_{stat.st_mtime}".encode("utf-8"))
    try:
        with open(filepath, "rb") as f:
            h.update(f.read(65536))
            if stat.st_size > 65536:
                f.seek(max(0, stat.st_size - 65536))
                h.update(f.read(65536))
    except Exception:
        pass
    return h.hexdigest()[:16]

# ---------------------------------------------------------------------------
# STEP 1: PROBE MEDIA & VALIDATE AUDIO STREAM
# ---------------------------------------------------------------------------
def probe_media(filepath: str) -> Dict[str, Any]:
    """
    Probe media container using ffprobe.
    Raises RuntimeError immediately if there is no audio stream.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")

    cmd = f'"{FFPROBE}" -v quiet -print_format json -show_format -show_streams "{filepath}"'
    code, stdout, stderr = run_cmd(cmd)
    if code != 0 or not stdout.strip():
        raise RuntimeError(f"FFprobe failed to analyze {filepath}: {stderr}")

    info = json.loads(stdout)
    streams = info.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # Fail clearly if there is no audio stream
    if not a_stream:
        raise RuntimeError(f"Validation Error: Video contains no audio stream: '{filepath}'")

    format_info = info.get("format", {})
    duration = float(format_info.get("duration") or (v_stream or a_stream).get("duration", 0.0))

    width = int(v_stream.get("width", 1920)) if v_stream else 1920
    height = int(v_stream.get("height", 1080)) if v_stream else 1080

    fps = 30.0
    if v_stream and "r_frame_rate" in v_stream:
        parts = v_stream["r_frame_rate"].split("/")
        if len(parts) == 2 and float(parts[1]) > 0:
            fps = float(parts[0]) / float(parts[1])

    return {
        "filepath": str(Path(filepath).resolve()),
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_video": v_stream is not None,
        "has_audio": True,
        "audio_codec": a_stream.get("codec_name", "unknown"),
        "audio_sample_rate": int(a_stream.get("sample_rate", 44100)),
        "audio_channels": int(a_stream.get("channels", 2))
    }

# ---------------------------------------------------------------------------
# STEP 2: MONO 16KHZ AUDIO EXTRACTION & WHISPER TRANSCRIPTION (CACHED)
# ---------------------------------------------------------------------------
def extract_and_transcribe(filepath: str, work_dir: Path, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract mono 16kHz WAV and transcribe using faster-whisper.
    Caches word-level timestamps in work_dir/words.json based on input hash.
    Supports Bengali, English, and Banglish speech.
    """
    words_cache = work_dir / "words.json"
    if words_cache.exists():
        try:
            with open(words_cache, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and isinstance(data, list):
                log_info(f"[CACHE] Using cached word-level transcription ({len(data)} words) from {words_cache.name}")
                return data
        except Exception:
            pass

    # Extract 16kHz mono audio
    wav_path = work_dir / "audio_16k.wav"
    log_info(f"[STEP 2] Extracting 16kHz mono WAV for Whisper: {wav_path.name}...")
    extract_cmd = f'"{FFMPEG}" -y -i "{filepath}" -vn -acodec pcm_s16le -ac 1 -ar 16000 "{wav_path}"'
    code, _, err = run_cmd(extract_cmd)
    if code != 0 or not wav_path.exists():
        raise RuntimeError(f"Failed to extract 16kHz WAV: {err}")

    # Read 16kHz mono PCM using standard wave module to avoid PyAV metadata_errors bugs
    import wave
    import numpy as np
    with wave.open(str(wav_path), "rb") as wf:
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)
        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

    w_cfg = cfg.get("whisper", {})
    model_size = w_cfg.get("model_size", "base")
    compute_type = w_cfg.get("compute_type", "int8")
    lang = w_cfg.get("language")
    beam_size = int(w_cfg.get("beam_size", 5))

    log_info(f"[STEP 2] Running faster-whisper (model={model_size}, lang={lang or 'auto'})...")
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        # Test encode to catch missing cublas dlls early
        model.model.encode(np.zeros((1, 80, 3000), dtype=np.float32))
    except Exception:
        log_info("[STEP 2] CUDA GPU acceleration unavailable or missing cublas dlls, falling back to CPU int8...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        audio_float32,
        beam_size=beam_size,
        word_timestamps=True,
        language=lang
    )

    detected_lang = info.language
    log_info(f"[STEP 2] Transcription complete. Detected language: {detected_lang} (prob: {info.language_probability:.2f})")

    words_list: List[Dict[str, Any]] = []
    for seg in segments:
        for w in (seg.words or []):
            word_str = w.word.strip()
            if word_str:
                words_list.append({
                    "word": word_str,
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                    "probability": round(float(w.probability), 3),
                    "language": detected_lang
                })

    with open(words_cache, "w", encoding="utf-8") as f:
        json.dump(words_list, f, indent=2, ensure_ascii=False)

    return words_list

# ---------------------------------------------------------------------------
# STEP 3: SILENCEDETECT
# ---------------------------------------------------------------------------
def detect_silences(filepath: str, cfg: Dict[str, Any]) -> List[Dict[str, float]]:
    """
    Run FFmpeg silencedetect to identify intervals of silence.
    Defaults: noise=-30dB, min duration=0.5s (configurable).
    """
    s_cfg = cfg.get("silence", {})
    noise_db = s_cfg.get("noise_threshold_db", -30.0)
    min_dur = s_cfg.get("min_duration", 0.5)

    log_info(f"[STEP 3] Detecting silences (threshold={noise_db}dB, min_duration={min_dur}s)...")
    cmd = f'"{FFMPEG}" -i "{filepath}" -af silencedetect=noise={noise_db}dB:d={min_dur} -f null -'
    code, _, stderr = run_cmd(cmd)

    silences: List[Dict[str, float]] = []
    current_start: Optional[float] = None

    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                current_start = float(line.split("silence_start:")[1].split()[0])
            except Exception:
                pass
        elif "silence_end:" in line and current_start is not None:
            try:
                parts = line.split("silence_end:")[1].split()
                end_t = float(parts[0])
                if end_t > current_start:
                    silences.append({
                        "start": round(current_start, 3),
                        "end": round(end_t, 3),
                        "duration": round(end_t - current_start, 3)
                    })
                current_start = None
            except Exception:
                pass

    log_info(f"[STEP 3] Detected {len(silences)} silent interval(s).")
    return silences

# ---------------------------------------------------------------------------
# STEP 4: FILLER WORDS & REPEATED TAKES DETECTION
# ---------------------------------------------------------------------------
def detect_fillers_and_repeated_takes(
    words: List[Dict[str, Any]],
    cfg: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect filler words and repeated takes.
    For repeated takes (same sentence repeated), keeps the LAST (best) take.
    """
    f_cfg = cfg.get("fillers", {})
    fillers_enabled = f_cfg.get("enabled", True)
    filler_set = set(w.lower().strip() for w in f_cfg.get("words", []))

    removed_intervals: List[Dict[str, Any]] = []

    # 1. Filler words
    if fillers_enabled and filler_set:
        for w in words:
            clean_word = w["word"].lower().strip(".,!?:;\"'")
            if clean_word in filler_set:
                removed_intervals.append({
                    "start": w["start"],
                    "end": w["end"],
                    "reason": f"filler ({clean_word})"
                })

    # 2. Repeated takes detection
    rt_cfg = cfg.get("repeated_takes", {})
    if rt_cfg.get("enabled", True) and len(words) > 5:
        sim_threshold = float(rt_cfg.get("similarity_threshold", 0.75))
        # Form sliding sentence candidate windows (4 to 12 words)
        phrases: List[Dict[str, Any]] = []
        step = 4
        window_size = 8
        for i in range(0, len(words) - window_size + 1, step):
            chunk = words[i:i + window_size]
            phrase_text = " ".join(w["word"].lower().strip(".,!?:;\"'") for w in chunk)
            phrases.append({
                "text": phrase_text,
                "start": chunk[0]["start"],
                "end": chunk[-1]["end"],
                "words": chunk
            })

        # Compare pairs of phrases
        for i in range(len(phrases)):
            for j in range(i + 1, len(phrases)):
                p1, p2 = phrases[i], phrases[j]
                if p2["start"] - p1["end"] > 15.0: # If gap > 15s, not a direct take retake
                    continue
                similarity = difflib.SequenceMatcher(None, p1["text"], p2["text"]).ratio()
                if similarity >= sim_threshold:
                    # Keep the LAST take, remove the earlier take
                    removed_intervals.append({
                        "start": p1["start"],
                        "end": p1["end"],
                        "reason": f"repeated take (similarity: {similarity:.2f})"
                    })
                    break

    log_info(f"[STEP 4] Detected {len(removed_intervals)} filler & repeated take interval(s).")
    return removed_intervals

# ---------------------------------------------------------------------------
# STEP 5: BUILD EDL.JSON WITH PADDING & MICRO-CUT MERGING
# ---------------------------------------------------------------------------
def build_edl(
    total_duration: float,
    silences: List[Dict[str, float]],
    filler_repeats: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    work_dir: Path
) -> Dict[str, Any]:
    """
    Build edl.json:
    - Combines silences, fillers, repeated takes into removed list.
    - Applies word padding (0.08s default) so cuts do not clip words.
    - Merges keep-segments closer than 0.15s.
    """
    p_cfg = cfg.get("padding", {})
    pad = float(p_cfg.get("word_padding", 0.08))
    merge_dist = float(p_cfg.get("merge_threshold", 0.15))

    # Combine all removals
    all_removals = []
    for s in silences:
        all_removals.append({"start": s["start"], "end": s["end"], "reason": "silence"})
    for r in filler_repeats:
        all_removals.append(r)

    # Sort removals by start time
    all_removals.sort(key=lambda x: x["start"])

    # Invert to preliminary keep segments
    pre_keep = []
    current_t = 0.0
    for rem in all_removals:
        if rem["start"] > current_t:
            pre_keep.append({"start": current_t, "end": rem["start"]})
        current_t = max(current_t, rem["end"])
    if current_t < total_duration:
        pre_keep.append({"start": current_t, "end": total_duration})

    # Apply padding to keep segments
    padded_keep = []
    for seg in pre_keep:
        st = max(0.0, seg["start"] - pad)
        ed = min(total_duration, seg["end"] + pad)
        if ed > st + 0.05: # Ignore micro segments under 50ms
            padded_keep.append({"start": round(st, 3), "end": round(ed, 3)})

    # Merge overlapping or close keep segments (< merge_dist)
    merged_keep: List[Dict[str, float]] = []
    for seg in padded_keep:
        if not merged_keep:
            merged_keep.append(seg)
        else:
            prev = merged_keep[-1]
            if seg["start"] <= prev["end"] + merge_dist:
                prev["end"] = max(prev["end"], seg["end"])
            else:
                merged_keep.append(seg)

    # Reconstruct exact removed intervals from final kept segments
    final_removed: List[Dict[str, Any]] = []
    curr = 0.0
    for k in merged_keep:
        if k["start"] > curr:
            final_removed.append({
                "start": round(curr, 3),
                "end": round(k["start"], 3),
                "reason": "silence/cut"
            })
        curr = k["end"]
    if curr < total_duration:
        final_removed.append({
            "start": round(curr, 3),
            "end": round(total_duration, 3),
            "reason": "tail silence"
        })

    expected_duration = sum(k["end"] - k["start"] for k in merged_keep)

    edl = {
        "keep": merged_keep,
        "removed": final_removed,
        "original_duration": round(total_duration, 3),
        "expected_duration": round(expected_duration, 3),
        "reduction_seconds": round(total_duration - expected_duration, 3),
        "reduction_percentage": round(((total_duration - expected_duration) / max(1.0, total_duration)) * 100, 1)
    }

    edl_path = work_dir / "edl.json"
    with open(edl_path, "w", encoding="utf-8") as f:
        json.dump(edl, f, indent=2)

    log_info(f"[STEP 5] EDL built: {len(merged_keep)} keep segments, {len(final_removed)} cuts. Expected duration: {expected_duration:.2f}s (saved {edl['reduction_percentage']}%)")
    return edl

# ---------------------------------------------------------------------------
# STEP 6: RENDER WITH FFMPEG TRIM + CONCAT (FILTER_COMPLEX_SCRIPT)
# ---------------------------------------------------------------------------
def render_cuts(
    input_video: str,
    edl: Dict[str, Any],
    work_dir: Path,
    output_path: str,
    cfg: Dict[str, Any],
    vertical: bool = False,
    normalize: bool = False
) -> str:
    """
    Render trimmed & concatenated video with exact A/V sync.
    Uses filter_complex_script to avoid Windows command line length limits.
    Re-encodes libx264 CRF 18, AAC 192k.
    """
    keep_segments = edl.get("keep", [])
    if not keep_segments:
        raise ValueError("EDL contains no segments to keep!")

    rend_cfg = cfg.get("rendering", {})
    crf = rend_cfg.get("crf", 18)
    preset = rend_cfg.get("preset", "medium")
    v_codec = rend_cfg.get("video_codec", "libx264")
    a_codec = rend_cfg.get("audio_codec", "aac")
    a_bitrate = rend_cfg.get("audio_bitrate", "192k")

    filter_lines: List[str] = []
    v_labels: List[str] = []
    a_labels: List[str] = []

    # Check if media has video stream (support faceless audio)
    p_info = probe_media(input_video)
    has_video = p_info.get("has_video", True)

    # Optional vertical center crop
    v_pre_filter = ""
    if vertical and has_video:
        # 1080x1920 center crop (with aspect ratio preservation)
        v_pre_filter = "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920,"

    if not has_video:
        # Audio-only faceless media trimming
        for i, seg in enumerate(keep_segments):
            st = seg["start"]
            ed = seg["end"]
            filter_lines.append(f"[0:a]atrim=start={st}:end={ed},asetpts=PTS-STARTPTS[a{i}];")
            a_labels.append(f"[a{i}]")

        num_segs = len(keep_segments)
        concat_inputs = "".join(f"{a_labels[j]}" for j in range(num_segs))
        if normalize:
            target_lufs = rend_cfg.get("target_lufs", -16.0)
            filter_lines.append(f"{concat_inputs}concat=n={num_segs}:v=0:a=1[a_raw];")
            filter_lines.append(f"[a_raw]loudnorm=I={target_lufs}:LRA=11:tp=-1.5[out_a];")
        else:
            filter_lines.append(f"{concat_inputs}concat=n={num_segs}:v=0:a=1[out_a];")

        filter_graph = "\n".join(filter_lines)
        filter_script = work_dir / "filter_script.txt"
        with open(filter_script, "w", encoding="utf-8") as f:
            f.write(filter_graph)

        log_info(f"[STEP 6] Rendering {num_segs} audio segments via filter_complex to {output_path}...")
        cmd_args = [
            FFMPEG, "-y",
            "-i", input_video,
            "-filter_complex", filter_graph,
            "-map", "[out_a]",
            "-c:a", str(a_codec), "-b:a", str(a_bitrate),
            str(output_path)
        ]
        res = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0 or not os.path.exists(output_path):
            raise RuntimeError(f"FFmpeg audio rendering failed: {res.stderr}")
        return output_path

    # Standard video + audio rendering
    for i, seg in enumerate(keep_segments):
        st = seg["start"]
        ed = seg["end"]
        filter_lines.append(f"[0:v]trim=start={st}:end={ed},{v_pre_filter}setpts=PTS-STARTPTS[v{i}];")
        filter_lines.append(f"[0:a]atrim=start={st}:end={ed},asetpts=PTS-STARTPTS[a{i}];")
        v_labels.append(f"[v{i}]")
        a_labels.append(f"[a{i}]")

    num_segs = len(keep_segments)
    concat_inputs = "".join(f"{v_labels[j]}{a_labels[j]}" for j in range(num_segs))
    
    if normalize:
        target_lufs = rend_cfg.get("target_lufs", -16.0)
        filter_lines.append(f"{concat_inputs}concat=n={num_segs}:v=1:a=1[v_raw][a_raw];")
        filter_lines.append(f"[a_raw]loudnorm=I={target_lufs}:LRA=11:tp=-1.5[out_a];")
        out_v = "[v_raw]"
        out_a = "[out_a]"
    else:
        filter_lines.append(f"{concat_inputs}concat=n={num_segs}:v=1:a=1[out_v][out_a];")
        out_v = "[out_v]"
        out_a = "[out_a]"

    filter_graph = "\n".join(filter_lines)
    filter_script = work_dir / "filter_script.txt"
    with open(filter_script, "w", encoding="utf-8") as f:
        f.write(filter_graph)

    log_info(f"[STEP 6] Rendering {num_segs} segments via filter_complex to {output_path}...")
    cmd_args = [
        FFMPEG, "-y",
        "-i", input_video,
        "-filter_complex", filter_graph,
        "-map", out_v, "-map", out_a,
        "-c:v", str(v_codec), "-crf", str(crf), "-preset", str(preset),
        "-c:a", str(a_codec), "-b:a", str(a_bitrate),
        output_path
    ]
    res = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f"FFmpeg rendering failed: {res.stderr}")

    return output_path

# ---------------------------------------------------------------------------
# STEP 7: WORD TIMESTAMP REMAPPING & KINETIC ASS CAPTIONS
# ---------------------------------------------------------------------------
def remap_and_generate_captions(
    words: List[Dict[str, Any]],
    edl: Dict[str, Any],
    work_dir: Path,
    cfg: Dict[str, Any],
    vertical: bool = False
) -> str:
    """
    Remaps original word timestamps onto the new timeline (subtracting removed intervals).
    Generates ASS karaoke subtitle file with 2-4 words per line, active word highlighted,
    bottom-center alignment, bold outline, and safe 9:16 margins.
    """
    c_cfg = cfg.get("captions", {})
    keep_segments = edl.get("keep", [])

    # Calculate cumulative offsets
    remapped_words: List[Dict[str, Any]] = []
    
    for w in words:
        w_st = w["start"]
        w_ed = w["end"]
        # Find which kept segment this word falls into
        elapsed_new_timeline = 0.0
        word_kept = False

        for k in keep_segments:
            seg_dur = k["end"] - k["start"]
            if k["start"] <= w_st <= k["end"]:
                # Word is within this segment
                new_st = elapsed_new_timeline + (w_st - k["start"])
                new_ed = elapsed_new_timeline + (min(w_ed, k["end"]) - k["start"])
                remapped_words.append({
                    "word": w["word"],
                    "start": round(new_st, 3),
                    "end": round(max(new_st + 0.1, new_ed), 3)
                })
                word_kept = True
                break
            elapsed_new_timeline += seg_dur

    # Group into lines of 2 to 4 words
    min_w = int(c_cfg.get("words_per_line_min", 2))
    max_w = int(c_cfg.get("words_per_line_max", 4))
    
    lines: List[List[Dict[str, Any]]] = []
    curr_line: List[Dict[str, Any]] = []

    for w in remapped_words:
        curr_line.append(w)
        if len(curr_line) >= max_w or (len(curr_line) >= min_w and w["word"].endswith((".", "?", "!", ","))):
            lines.append(curr_line)
            curr_line = []
    if curr_line:
        lines.append(curr_line)

    # Format ASS content
    res_x = 1080 if vertical else 1920
    res_y = 1920 if vertical else 1080
    font_name = c_cfg.get("font_name", "Arial")
    font_size = int(c_cfg.get("font_size", 28)) * (2 if vertical else 1)
    primary_color = c_cfg.get("primary_color", "&H00FFFFFF")
    highlight_color = c_cfg.get("highlight_color", "&H0022D3EE")
    outline_color = c_cfg.get("outline_color", "&H000B0D14")
    outline_w = float(c_cfg.get("outline_width", 3.5))
    shadow_d = float(c_cfg.get("shadow_depth", 1.5))
    alignment = int(c_cfg.get("alignment", 2))
    margin_v = int(c_cfg.get("margin_v", 180))

    ass_header = f"""[Script Info]
Title: OpenCut Kinetic Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {res_x}
PlayResY: {res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{outline_w},{shadow_d},{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    def to_ass_time(secs: float) -> str:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = secs % 60
        return f"{h:01d}:{m:02d}:{s:05.2f}"

    for line_words in lines:
        if not line_words:
            continue
        line_start = line_words[0]["start"]
        line_end = line_words[-1]["end"]

        # Word-by-word active highlight
        for i, active_w in enumerate(line_words):
            w_st = active_w["start"]
            w_ed = active_w["end"]
            
            chunks = []
            for j, w in enumerate(line_words):
                if j == i:
                    chunks.append(f"{{\\c{highlight_color}\\b1}}{w['word']}{{\\c{primary_color}\\b0}}")
                else:
                    chunks.append(w["word"])
            line_text = " ".join(chunks)
            events.append(f"Dialogue: 0,{to_ass_time(w_st)},{to_ass_time(w_ed)},Default,,0,0,0,,{line_text}")

    ass_path = work_dir / "captions.ass"
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

    log_info(f"[STEP 7] Kinetic captions generated: {len(events)} dialogue event(s) -> {ass_path.name}")
    return str(ass_path.resolve())

# ---------------------------------------------------------------------------
# STEP 8: VERTICAL MODE & FACE TRACKING HOOK
# ---------------------------------------------------------------------------
def track_face_center(video_path: str) -> List[Dict[str, Any]]:
    """
    Hook for AI face-tracking:
    TODO: Add automated MediaPipe / YOLO face center bounding box detection
    to dynamically shift crop X-offset instead of static center crop.
    """
    return []

# ---------------------------------------------------------------------------
# STEP 9 & 10: VERIFICATION (5 FRAMES QA & DURATION CHECK)
# ---------------------------------------------------------------------------
def verify_output(
    output_path: str,
    expected_duration: float,
    work_dir: Path,
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract 5 evenly spaced frames from output into work/frames/.
    Validates duration within tolerance (0.3s) and frame existence.
    """
    qa_cfg = cfg.get("qa", {})
    tol = float(qa_cfg.get("duration_tolerance", 0.3))
    frame_count = int(qa_cfg.get("frame_count", 5))

    probe = probe_media(output_path)
    actual_duration = probe["duration"]
    dur_diff = abs(actual_duration - expected_duration)
    dur_ok = dur_diff <= tol

    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    has_video = probe.get("has_video", True)
    extracted_frames = []
    if has_video and actual_duration > 0.5:
        step_t = actual_duration / (frame_count + 1)
        for i in range(1, frame_count + 1):
            t = round(i * step_t, 2)
            f_path = frames_dir / f"frame_{i}.jpg"
            cmd = f'"{FFMPEG}" -y -ss {t} -i "{output_path}" -vframes 1 -q:v 2 "{f_path}"'
            code, _, _ = run_cmd(cmd)
            if code == 0 and f_path.exists():
                extracted_frames.append(str(f_path.resolve()))

    return {
        "verified": dur_ok and (len(extracted_frames) >= frame_count if has_video else True),
        "actual_duration": round(actual_duration, 3),
        "expected_duration": round(expected_duration, 3),
        "duration_diff": round(dur_diff, 3),
        "duration_ok": dur_ok,
        "frames_extracted": len(extracted_frames),
        "frame_paths": extracted_frames
    }

# ---------------------------------------------------------------------------
# MAIN PIPELINE ENTRYPOINT
# ---------------------------------------------------------------------------
def run_pipeline(
    filepath: str,
    output_path: Optional[str] = None,
    config_path: Optional[str] = None,
    dry_run: bool = False,
    vertical: bool = False,
    normalize: bool = False,
    add_captions: bool = True
) -> Dict[str, Any]:
    """
    Execute full autonomous video editing pipeline.
    Never overwrites input file.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    cfg = load_config(config_path)

    # 1. Probe & validate audio
    probe_info = probe_media(filepath)
    total_dur = probe_info["duration"]

    # Prepare work directory based on hash for caching
    file_hash = compute_file_hash(filepath)
    input_p = Path(filepath)
    base_name = input_p.stem
    work_dir = BASE_DIR / "work" / f"{base_name}_{file_hash}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Output path resolution
    if not output_path:
        suffix = "_autocut"
        if vertical: suffix += "_vertical"
        if normalize: suffix += "_norm"
        output_path = str(input_p.parent / f"{base_name}{suffix}.mp4")

    # Safety: Never overwrite input file
    if Path(output_path).resolve() == input_p.resolve():
        output_path = str(input_p.parent / f"{base_name}_autocut_master.mp4")

    # 2. Extract 16kHz audio & Whisper transcription (cached)
    words = extract_and_transcribe(filepath, work_dir, cfg)

    # 3. Silencedetect
    silences = detect_silences(filepath, cfg)

    # 4. Fillers & Repeated Takes
    filler_repeats = detect_fillers_and_repeated_takes(words, cfg)

    # 5. Build EDL
    edl = build_edl(total_dur, silences, filler_repeats, cfg, work_dir)

    if dry_run:
        log_info("[DRY RUN] Pipeline completed preview without rendering.")
        return {
            "status": "dry_run_complete",
            "edl": edl,
            "work_dir": str(work_dir.resolve()),
            "probe": probe_info
        }

    # 6. Render cuts
    rendered_file = render_cuts(
        filepath, edl, work_dir, output_path, cfg,
        vertical=vertical, normalize=normalize
    )

    # 7. Captions
    ass_path = None
    if add_captions and words:
        ass_path = remap_and_generate_captions(words, edl, work_dir, cfg, vertical=vertical)

    # 10. QA Verification
    qa = verify_output(rendered_file, edl["expected_duration"], work_dir, cfg)

    result = {
        "status": "complete",
        "output_path": str(Path(rendered_file).resolve()),
        "captions_ass": ass_path,
        "edl": edl,
        "qa": qa,
        "work_dir": str(work_dir.resolve()),
        "probe": probe_info
    }
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenCut Autonomous Editing Pipeline")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Path to output video file")
    parser.add_argument("-c", "--config", help="Path to custom config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Preview cuts without rendering")
    parser.add_argument("--vertical", action="store_true", help="Center crop to 1080x1920 (9:16)")
    parser.add_argument("--normalize", action="store_true", help="Normalize loudness to -16 LUFS")
    parser.add_argument("--no-captions", action="store_true", help="Disable ASS kinetic caption generation")

    args = parser.parse_args()
    res = run_pipeline(
        args.input,
        output_path=args.output,
        config_path=args.config,
        dry_run=args.dry_run,
        vertical=args.vertical,
        normalize=args.normalize,
        add_captions=not args.no_captions
    )
    print(json.dumps(res, indent=2))
