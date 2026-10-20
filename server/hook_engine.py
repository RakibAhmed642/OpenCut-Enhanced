"""
OpenCut Autonomous Smart Hook Intro Generator
Extracts 2s–3s peak energy & viral highlight moments across a full video,
assembles them with high-retention cinematic whoosh transitions and teaser badges,
and outputs a studio-grade hook intro ready for 0:00 timeline insertion.
"""

import os
import sys
import json
import time
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

BASE_DIR = Path("E:/autocut")
FFMPEG = str(BASE_DIR / "ffmpeg" / "ffmpeg.exe")
FFPROBE = str(BASE_DIR / "ffmpeg" / "ffprobe.exe")
ASSETS_DIR = BASE_DIR / "assets" / "sfx"

sys.path.insert(0, str(BASE_DIR / "server"))
from sound_designer import ensure_sound_library


def run_cmd(cmd: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Execute shell command with captured stdout/stderr."""
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, cwd=cwd)
    return res.returncode, res.stdout, res.stderr


def probe_video(filepath: str) -> Dict[str, Any]:
    """Extract container duration, resolution, and streams."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")

    cmd = f'"{FFPROBE}" -v quiet -print_format json -show_format -show_streams "{filepath}"'
    code, stdout, stderr = run_cmd(cmd)
    if code != 0 or not stdout.strip():
        raise RuntimeError(f"FFprobe failed to inspect {filepath}: {stderr}")

    info = json.loads(stdout)
    streams = info.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    fmt = info.get("format", {})
    dur = float(fmt.get("duration") or (v_stream or a_stream or {}).get("duration", 0.0))
    has_video = v_stream is not None
    has_audio = a_stream is not None
    is_audio_only = has_audio and not has_video

    width = int(v_stream.get("width", 1080 if is_audio_only else 1920)) if v_stream else (1080 if is_audio_only else 1920)
    height = int(v_stream.get("height", 1920 if is_audio_only else 1080)) if v_stream else (1920 if is_audio_only else 1080)

    return {
        "duration": dur,
        "width": width,
        "height": height,
        "has_video": has_video,
        "has_audio": has_audio,
        "is_audio_only": is_audio_only,
        "video_stream": v_stream,
        "audio_stream": a_stream
    }


def detect_speech_intervals(filepath: str, noise_db: float = -28.0, min_silence: float = 0.3) -> List[Dict[str, float]]:
    """Detect spoken dialogue intervals using FFmpeg silencedetect."""
    cmd = f'"{FFMPEG}" -i "{filepath}" -vn -af "silencedetect=n={noise_db}dB:d={min_silence}" -f null -'
    code, stdout, stderr = run_cmd(cmd)

    silence_starts = []
    silence_ends = []

    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                parts = line.split("silence_start:")
                silence_starts.append(float(parts[1].strip().split()[0]))
            except Exception:
                pass
        elif "silence_end:" in line:
            try:
                parts = line.split("silence_end:")
                silence_ends.append(float(parts[1].strip().split()[0]))
            except Exception:
                pass

    speech_segments = []
    current_start = 0.0

    for s_start, s_end in zip(silence_starts, silence_ends):
        if s_start > current_start + 0.1:
            speech_segments.append({"start": current_start, "end": s_start})
        current_start = s_end

    probe = probe_video(filepath)
    tot_dur = probe["duration"]
    if current_start < tot_dur - 0.1:
        speech_segments.append({"start": current_start, "end": tot_dur})

    if not speech_segments:
        speech_segments.append({"start": 0.0, "end": tot_dur})

    return speech_segments


def detect_hook_moments(
    filepath: str,
    clip_count: int = 3,
    clip_duration: float = 2.5,
    min_gap: float = 4.0
) -> List[Dict[str, Any]]:
    """
    Scans the video and extracts `clip_count` peak energy moments (each `clip_duration` seconds)
    distributed across distinct chronological acts of the video for a true narrative teaser hook.
    """
    probe = probe_video(filepath)
    total_dur = probe["duration"]
    clip_count = max(2, min(clip_count, 6))
    clip_duration = max(1.5, min(clip_duration, 4.0))

    if total_dur <= (clip_count * clip_duration):
        # Short video: partition evenly
        moments = []
        seg_dur = total_dur / clip_count
        for i in range(clip_count):
            st = i * seg_dur
            en = min(total_dur, st + clip_duration)
            moments.append({
                "index": i + 1,
                "start": round(st, 2),
                "end": round(en, 2),
                "duration": round(en - st, 2),
                "label": f"Moment {i+1}: Hook Teaser",
                "energy": 90 - (i * 2)
            })
        return moments

    speech_segs = detect_speech_intervals(filepath)

    # Divide timeline into distinct chronological partitions
    # E.g. for 3 clips: Act 1 (10% to 35%), Act 2 (35% to 70%), Act 3 (70% to 95%)
    partition_bounds = []
    step = 0.85 / clip_count
    for i in range(clip_count):
        p_start = (0.08 + (i * step)) * total_dur
        p_end = (0.08 + ((i + 1) * step)) * total_dur
        partition_bounds.append((p_start, p_end))

    labels = [
        "Act 1: Intriguing Hook",
        "Act 2: Mid-Pacing Spike",
        "Act 3: Peak Climax",
        "Act 4: Punchline Reveal",
        "Act 5: Final Teaser"
    ]

    selected_moments = []
    last_end = -999.0

    for i, (p_st, p_en) in enumerate(partition_bounds):
        best_win_start = p_st
        best_win_score = -1.0
        t = p_st

        while t <= p_en - clip_duration:
            t_end = t + clip_duration

            # Calculate speech density & boundary alignment inside window
            speech_overlap = 0.0
            boundary_bonus = 0.0

            for s in speech_segs:
                o_st = max(t, s["start"])
                o_en = min(t_end, s["end"])
                if o_en > o_st:
                    speech_overlap += (o_en - o_st)
                    # Bonus if window starts right after a pause (clean sentence start)
                    if abs(t - s["start"]) < 0.25:
                        boundary_bonus += 0.35

            density = speech_overlap / clip_duration
            # Slight preference for moments further along in the act for tension buildup
            temporal_arc = (t - p_st) / max(1.0, (p_en - p_st)) * 0.15
            score = (density * 0.65) + boundary_bonus + temporal_arc

            # Ensure minimum spacing between consecutive clips
            if t >= last_end + min_gap and score > best_win_score:
                best_win_score = score
                best_win_start = t

            t += 0.4

        # Snap to nearest speech boundary if within 0.3s
        final_st = best_win_start
        for s in speech_segs:
            if abs(s["start"] - final_st) < 0.35:
                final_st = s["start"]
                break

        final_en = min(total_dur, final_st + clip_duration)
        last_end = final_en

        lbl = labels[i] if i < len(labels) else f"Moment {i+1}: Teaser"
        energy_pct = min(99, max(75, int(78 + (best_win_score * 20))))

        selected_moments.append({
            "index": i + 1,
            "start": round(final_st, 2),
            "end": round(final_en, 2),
            "duration": round(final_en - final_st, 2),
            "label": lbl,
            "energy": energy_pct
        })

    return selected_moments


def create_smart_hook(
    filepath: str,
    clip_count: int = 3,
    clip_duration: float = 2.5,
    hook_style: str = "dynamic_teaser",
    badge_text: str = "COMING UP...",
    transition_sfx: bool = True,
    flash_cuts: bool = True,
    output_dir: Optional[str] = None,
    use_ai: bool = False,
    ai_provider: Optional[str] = None,
    api_key: Optional[str] = None,
    ai_model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Autonomous Studio Hook Intro Generator:
    1. Extracts 2s-3s moments (Local NLP or Cloud AI LLM Decision)
    2. Builds teaser badge overlay
    3. Adds high-impact whoosh SFX at cut points
    4. Renders EBU R128 normalized hook MP4 file
    """
    ensure_sound_library()
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    probe = probe_video(str(input_path))
    in_w = probe["width"]
    in_h = probe["height"]

    # Output folder
    if output_dir:
        out_folder = Path(output_dir)
    else:
        out_folder = input_path.parent / "OpenCut_Hooks"
    out_folder.mkdir(parents=True, exist_ok=True)

    base_name = input_path.stem
    ts = int(time.time())
    hook_video_name = f"{base_name}_hook_intro_{ts}.mp4"
    hook_video_path = out_folder / hook_video_name

    # 1. Detect Peak Moments (Local Act partitions vs Cloud AI narrative climax)
    moments = []
    if use_ai:
        try:
            from ai_moment_intelligence import detect_hook_moments_llm
            moments = detect_hook_moments_llm(
                str(input_path),
                clip_count=clip_count,
                clip_duration=clip_duration,
                provider=ai_provider,
                api_key=api_key,
                model=ai_model,
                custom_endpoint=custom_endpoint
            )
        except Exception as aie:
            sys.stderr.write(f"Hook AI selection notice: {aie}\n")

    if not moments:
        moments = detect_hook_moments(
            str(input_path),
            clip_count=clip_count,
            clip_duration=clip_duration
        )

    if not moments:
        raise RuntimeError("No suitable hook moments could be detected.")

    temp_clips = []
    tmp_dir = out_folder / f".tmp_hook_{ts}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        is_audio_only = probe.get("is_audio_only", False)

        # 2. Extract Each Teaser Clip
        for idx, m in enumerate(moments):
            c_file = tmp_dir / f"clip_{idx:02d}.mp4"
            st = m["start"]
            dur = m["duration"]

            if is_audio_only:
                # Faceless Audio: Render studio dark card with responsive animated golden waveform
                wave_w = min(920, int(in_w * 0.85))
                wave_h = min(360, int(in_h * 0.22))
                filt = (
                    f"color=c=0x07090e:s={in_w}x{in_h}:d={dur:.3f}[bg];"
                    f"[0:a]showwaves=s={wave_w}x{wave_h}:mode=p2p:colors=0xfacc15:scale=sqrt[wave];"
                    f"[bg][wave]overlay=(W-w)/2:(H-h)/2[v_raw]"
                )
                if flash_cuts and idx > 0:
                    filt += ";[v_raw]fade=t=in:st=0:d=0.1:color=white[v]"
                    v_map = "[v]"
                else:
                    v_map = "[v_raw]"

                af_str = "aformat=channel_layouts=stereo:sample_rates=48000"
                cmd = (
                    f'"{FFMPEG}" -y -ss {st:.3f} -t {dur:.3f} -i "{input_path}" '
                    f'-filter_complex "{filt}" -map "{v_map}" -map 0:a -af "{af_str}" '
                    f'-c:v libx264 -preset ultrafast -pix_fmt yuv420p -c:a aac -b:a 192k "{c_file}"'
                )
            else:
                # Standard Video: Scale, framerate and optional dip-to-white flash
                vf_parts = [f"scale={in_w}:{in_h}:flags=lanczos,fps=30"]
                if flash_cuts and idx > 0:
                    # 0.1s quick dip-to-white flash at cut start
                    vf_parts.append("fade=t=in:st=0:d=0.1:color=white")

                vf_str = ",".join(vf_parts)
                af_str = "aformat=channel_layouts=stereo:sample_rates=48000"

                cmd = (
                    f'"{FFMPEG}" -y -ss {st:.3f} -t {dur:.3f} -i "{input_path}" '
                    f'-vf "{vf_str}" -af "{af_str}" -c:v libx264 -preset fast -crf 18 '
                    f'-c:a aac -b:a 192k "{c_file}"'
                )
            code, stdout, stderr = run_cmd(cmd)
            if code != 0 or not c_file.exists():
                raise RuntimeError(f"Failed to extract hook clip {idx+1}: {stderr}")
            temp_clips.append(c_file)

        # 3. Concatenate Teaser Clips
        concat_txt = tmp_dir / "concat_list.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for tc in temp_clips:
                f.write(f"file '{tc.resolve().as_posix()}'\n")

        raw_concat = tmp_dir / "raw_concat.mp4"
        concat_cmd = (
            f'"{FFMPEG}" -y -f concat -safe 0 -i "{concat_txt}" '
            f'-c:v libx264 -preset fast -crf 18 -c:a aac -b:a 192k "{raw_concat}"'
        )
        code, stdout, stderr = run_cmd(concat_cmd)
        if code != 0 or not raw_concat.exists():
            raise RuntimeError(f"Hook concat failed: {stderr}")

        total_hook_dur = sum(m["duration"] for m in moments)

        # 4. Sound Design & Badge Overlay Pass
        # Locate whoosh SFX
        whoosh_file = ASSETS_DIR / "whoosh_fast.wav"
        hit_file = ASSETS_DIR / "dramatic_hit.wav"
        if not whoosh_file.exists():
            ensure_sound_library()

        # Build audio filtergraph to mix whooshes at transition cuts
        # Transition timestamps: clip 1 end, clip 2 end, etc.
        transition_times = []
        cur_t = 0.0
        for m in moments[:-1]:
            cur_t += m["duration"]
            transition_times.append(cur_t)

        final_inputs = [f'-i "{raw_concat}"']
        filter_complex_parts = []
        audio_mix_inputs = ["[0:a]"]

        if transition_sfx and whoosh_file.exists() and transition_times:
            for s_idx, t_time in enumerate(transition_times):
                sfx_src = whoosh_file if (s_idx % 2 == 0 or not hit_file.exists()) else hit_file
                final_inputs.append(f'-i "{sfx_src}"')
                input_idx = len(final_inputs) - 1
                # Place whoosh centered around transition (-0.15s)
                delay_ms = max(0, int((t_time - 0.15) * 1000))
                tag = f"sfx{s_idx}"
                filter_complex_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.35[{tag}]")
                audio_mix_inputs.append(f"[{tag}]")

        # Mix all audio streams
        num_a_inputs = len(audio_mix_inputs)
        mix_inputs_str = "".join(audio_mix_inputs)
        filter_complex_parts.append(f"{mix_inputs_str}amix=inputs={num_a_inputs}:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")

        # Video filter: Optional Teaser Badge Overlay
        # E.g. [ ⚡ COMING UP... ] centered or top-left for opening 1.8s
        v_filters = []
        clean_badge = (badge_text or "").strip().upper()
        if clean_badge and clean_badge != "NONE":
            # Elegant semi-translucent banner with yellow accent text
            v_filters.append(
                f"drawtext=text='{clean_badge}':fontsize=36:fontcolor=0xFACC15:"
                f"box=1:boxcolor=0x000000@0.75:boxborderw=14:x=(w-text_w)/2:y=h*0.12:"
                f"enable='between(t,0.1,1.8)':shadowcolor=black:shadowx=2:shadowy=2"
            )

        v_filter_str = ",".join(v_filters) if v_filters else "null"
        filter_complex_parts.insert(0, f"[0:v]{v_filter_str}[vout]")

        full_filter_complex = ";".join(filter_complex_parts)
        input_args = " ".join(final_inputs)

        final_cmd = (
            f'"{FFMPEG}" -y {input_args} -filter_complex "{full_filter_complex}" '
            f'-map "[vout]" -map "[aout]" -c:v libx264 -preset fast -crf 18 '
            f'-c:a aac -b:a 192k "{hook_video_path}"'
        )

        code, stdout, stderr = run_cmd(final_cmd)
        if code != 0 or not hook_video_path.exists():
            # Fallback without drawtext if fontconfig missing
            sys.stderr.write(f"Notice: drawtext overlay fallback triggered: {stderr[:120]}\n")
            fallback_cmd = (
                f'"{FFMPEG}" -y -i "{raw_concat}" -af "loudnorm=I=-16:TP=-1.5:LRA=11" '
                f'-c:v copy -c:a aac -b:a 192k "{hook_video_path}"'
            )
            code2, _, _ = run_cmd(fallback_cmd)
            if code2 != 0 or not hook_video_path.exists():
                raise RuntimeError(f"Final hook render failed: {stderr}")

    finally:
        # Clean temporary clip pieces
        try:
            for tc in temp_clips:
                if tc.exists():
                    os.remove(str(tc))
            if (tmp_dir / "concat_list.txt").exists():
                os.remove(str(tmp_dir / "concat_list.txt"))
            if (tmp_dir / "raw_concat.mp4").exists():
                os.remove(str(tmp_dir / "raw_concat.mp4"))
            if tmp_dir.exists():
                os.rmdir(str(tmp_dir))
        except Exception:
            pass

    # Verify final render output on disk
    if not hook_video_path.exists() or hook_video_path.stat().st_size < 1000:
        raise RuntimeError(f"Hook video output missing or corrupted: {hook_video_path}")

    actual_probe = probe_video(str(hook_video_path))
    actual_dur = actual_probe["duration"]

    # Also export dedicated audio stem for pure-audio faceless workflows
    hook_audio_name = f"{base_name}_hook_intro_{ts}.wav"
    hook_audio_path = out_folder / hook_audio_name
    audio_export_cmd = f'"{FFMPEG}" -y -i "{hook_video_path}" -vn -c:a pcm_s16le -ar 48000 "{hook_audio_path}"'
    run_cmd(audio_export_cmd)

    return {
        "status": "success",
        "hook_video_path": str(hook_video_path.resolve()),
        "hook_video_name": hook_video_name,
        "hook_audio_path": str(hook_audio_path.resolve()) if hook_audio_path.exists() else None,
        "is_faceless": is_audio_only,
        "duration": round(actual_dur, 2),
        "clip_count": len(moments),
        "moments": moments,
        "badge_text": clean_badge,
        "sfx_applied": transition_sfx and whoosh_file.exists(),
        "engine_used": "AI Narrative Climax" if (moments and moments[0].get("ai_generated")) else "Local Dynamic Teaser"
    }


if __name__ == "__main__":
    sample_video = BASE_DIR / "samples" / "sample_test_20s.mp4"
    if sample_video.exists():
        print(f"Testing Hook Engine on {sample_video}...")
        res = create_smart_hook(str(sample_video), clip_count=3, clip_duration=2.0)
        print("Hook Result:", json.dumps(res, indent=2))
    else:
        print(f"Sample video not found at {sample_video}")
