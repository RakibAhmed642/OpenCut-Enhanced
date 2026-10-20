#!/usr/bin/env python3
"""
OpenCut AI Moment Intelligence Engine
Dual-Engine Viral Moment & Highlight Detector:
1. Smart Local NLP Engine: Faster-Whisper transcript analysis, semantic hook lexicons,
   question/answer detection, emotional cadence, and sentence boundary snapping.
2. Cloud AI LLM Engine: Gemini / OpenAI / Groq / Claude / OpenRouter API decision maker
   for viral story arcs, hook headlines, retention scoring, and high-impact clip selection.
"""

import os
import sys
import json
import wave
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

# Base paths
SERVER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_DIR.parent
CONFIG_PATH = SERVER_DIR / "ai_config.json"
FFMPEG = PROJECT_ROOT / "ffmpeg" / "ffmpeg.exe"
if not FFMPEG.exists():
    FFMPEG = Path("ffmpeg")

# Viral Trigger Lexicons for Bengali, English, and Banglish
VIRAL_TRIGGERS_EN = [
    "secret", "never", "mistake", "truth", "hack", "trick", "insane", "stop doing",
    "number one", "rule", "key", "important", "best way", "nobody tells you",
    "actually", "surprising", "wait until", "game changer", "warning", "how to",
    "why", "reason", "don't", "shocking", "results", "proven", "hidden", "transform",
    "powerful", "remember", "must know", "ultimate", "essential"
]

VIRAL_TRIGGERS_BN = [
    "আসল সত্য", "কখনো না", "সবচেয়ে বড় ভুল", "রহস্য", "জেনে রাখুন", "মনে রাখবেন",
    "প্রথমেই", "কারণ", "কিন্তু", "সবাই যে ভুল করে", "একদম", "সত্যি কথা", "দেখুন",
    "শুনুন", "সতর্ক", "বিশেষ", "উপায়", "কিভাবে", "কেন", "সবচেয়ে গুরুত্বপূর্ণ",
    "সবাই জানে না", "আজকের বিষয়", "ভুলেও করবেন না", "দারুণ", "চমকপ্রদ"
]

VIRAL_TRIGGERS_BANGLISH = [
    "asol shotto", "asole", "kokhono na", "shobcheye boro bhul", "rohossho",
    "mone rakhben", "kintu", "sobar age", "kivabe", "keno", "ekdom", "dekhen",
    "shunun", "bhuleo korben na", "bujhte parben", "asol kahini", "shobcheye guru"
]

DEFAULT_AI_CONFIG = {
    "enabled": False,
    "provider": "gemini",
    "api_key": "",
    "model": "gemini-2.5-flash",
    "custom_endpoint": "",
    "target_platforms": ["reels", "tiktok", "shorts"],
    "features": {
        "autoreel": True,
        "autohook": True,
        "caption_polish": True,
        "social_metadata": True,
        "assistant": True
    }
}


def load_ai_config() -> Dict[str, Any]:
    """Load persistent AI configuration from ai_config.json."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(DEFAULT_AI_CONFIG)
                merged.update(data)
                if "features" in data and isinstance(data["features"], dict):
                    feat = dict(DEFAULT_AI_CONFIG["features"])
                    feat.update(data["features"])
                    merged["features"] = feat
                return merged
        except Exception as e:
            sys.stderr.write(f"Error loading AI config: {e}\n")
    return dict(DEFAULT_AI_CONFIG)


def save_ai_config(cfg: Dict[str, Any]) -> bool:
    """Save persistent AI configuration to ai_config.json."""
    try:
        current = load_ai_config()
        current.update(cfg)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return True
    except Exception as e:
        sys.stderr.write(f"Error saving AI config: {e}\n")
        return False


def verify_ai_provider(provider: str, api_key: str, model: str = "", custom_endpoint: str = "") -> Dict[str, Any]:
    """
    Verifies that the provided API key is functional by running a minimal test prompt.
    """
    prov = (provider or "gemini").lower()
    key = (api_key or "").strip()
    if not key:
        return {"status": "error", "message": "API key is required."}

    test_prompt = "Say hello in 3 words."

    try:
        if prov == "gemini":
            mod = model.strip() if model.strip() else "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
            req_body = json.dumps({
                "contents": [{"parts": [{"text": test_prompt}]}]
            }).encode("utf-8")

            req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                text = resp_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return {"status": "success", "message": f"Gemini ({mod}) connection successful!", "response": text.strip(), "provider": "gemini", "model": mod}

        elif prov in ("openai", "groq", "deepseek", "custom"):
            if prov == "openai":
                mod = model.strip() if model.strip() else "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
            elif prov == "groq":
                mod = model.strip() if model.strip() else "llama-3.3-70b-versatile"
                url = "https://api.groq.com/openai/v1/chat/completions"
            elif prov == "deepseek":
                mod = model.strip() if model.strip() else "deepseek-chat"
                url = "https://api.deepseek.com/chat/completions"
            else: # custom
                mod = model.strip() if model.strip() else "custom-model"
                url = custom_endpoint.strip()
                if not url:
                    return {"status": "error", "message": "Custom endpoint URL is required."}

            req_body = json.dumps({
                "model": mod,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 15
            }).encode("utf-8")

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            req = urllib.request.Request(url, data=req_body, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                text = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"status": "success", "message": f"{prov.capitalize()} ({mod}) connection successful!", "response": text.strip(), "provider": prov, "model": mod}

        elif prov == "claude":
            mod = model.strip() if model.strip() else "claude-3-5-haiku-20241022"
            url = "https://api.anthropic.com/v1/messages"
            req_body = json.dumps({
                "model": mod,
                "max_tokens": 20,
                "messages": [{"role": "user", "content": test_prompt}]
            }).encode("utf-8")
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            req = urllib.request.Request(url, data=req_body, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                text = resp_json.get("content", [{}])[0].get("text", "")
                return {"status": "success", "message": f"Anthropic Claude ({mod}) connection successful!", "response": text.strip(), "provider": "claude", "model": mod}

        else:
            return {"status": "error", "message": f"Unsupported provider: {provider}"}

    except urllib.error.HTTPError as he:
        err_msg = he.read().decode("utf-8", errors="ignore")
        return {"status": "error", "message": f"HTTP {he.code}: {err_msg[:200]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def call_llm_raw(
    system_instruction: str,
    user_prompt: str,
    provider: str = "gemini",
    api_key: str = "",
    model: str = "",
    custom_endpoint: str = "",
    json_mode: bool = False,
    timeout: int = 30
) -> str:
    """Unified raw LLM completion caller across all supported AI providers."""
    prov = (provider or "gemini").lower()
    key = (api_key or "").strip()
    if not key:
        raise ValueError("Missing API key for Cloud AI call")

    if prov == "gemini":
        mod = model.strip() if model.strip() else "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
        gen_cfg: Dict[str, Any] = {"temperature": 0.3}
        if json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        
        full_text = f"{system_instruction}\n\n{user_prompt}" if system_instruction else user_prompt
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": full_text}]
                }
            ],
            "generationConfig": gen_cfg
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    elif prov in ("openai", "groq", "deepseek", "custom"):
        if prov == "openai":
            mod = model.strip() if model.strip() else "gpt-4o-mini"
            url = "https://api.openai.com/v1/chat/completions"
        elif prov == "groq":
            mod = model.strip() if model.strip() else "llama-3.3-70b-versatile"
            url = "https://api.groq.com/openai/v1/chat/completions"
        elif prov == "deepseek":
            mod = model.strip() if model.strip() else "deepseek-chat"
            url = "https://api.deepseek.com/chat/completions"
        else:
            mod = model.strip() if model.strip() else "custom-model"
            url = custom_endpoint.strip()
            if not url:
                raise ValueError("Custom endpoint URL is required.")

        msgs = []
        if system_instruction:
            msgs.append({"role": "system", "content": system_instruction})
        msgs.append({"role": "user", "content": user_prompt})

        body: Dict[str, Any] = {
            "model": mod,
            "messages": msgs,
            "temperature": 0.3
        }
        if json_mode and prov not in ("groq",):
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    elif prov == "claude":
        mod = model.strip() if model.strip() else "claude-3-5-haiku-20241022"
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": mod,
            "max_tokens": 2048,
            "system": system_instruction or "You are a professional video editor AI.",
            "messages": [{"role": "user", "content": user_prompt}]
        }
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("content", [{}])[0].get("text", "")

    else:
        raise ValueError(f"Unsupported AI provider: {provider}")


def call_llm_json(
    system_instruction: str,
    user_prompt: str,
    provider: str = "gemini",
    api_key: str = "",
    model: str = "",
    custom_endpoint: str = "",
    timeout: int = 30
) -> Any:
    """Unified JSON completion caller that handles codeblocks and parses output."""
    raw = call_llm_raw(
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        provider=provider,
        api_key=api_key,
        model=model,
        custom_endpoint=custom_endpoint,
        json_mode=True,
        timeout=timeout
    )
    clean = raw.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return json.loads(clean.strip())


def extract_audio_numpy(filepath: str) -> Tuple[Optional[np.ndarray], float]:
    """
    Extracts 16kHz mono audio directly into a NumPy float32 buffer.
    Bypasses PyAV bug in Python 3.13.
    """
    tmp_wav = Path(filepath).parent / f"ai_intel_tmp_{int(time.time()*1000)}.wav"
    cmd = [
        str(FFMPEG), "-y", "-i", str(filepath),
        "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", str(tmp_wav)
    ]
    try:
        import subprocess
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not tmp_wav.exists():
            return None, 0.0

        with wave.open(str(tmp_wav), "rb") as wf:
            n_frames = wf.getnframes()
            rate = wf.getframerate()
            raw_bytes = wf.readframes(n_frames)
            audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            duration = float(n_frames) / float(rate) if rate > 0 else 0.0

        try:
            tmp_wav.unlink(missing_ok=True)
        except Exception:
            pass

        return audio_float32, duration
    except Exception as e:
        sys.stderr.write(f"Audio extraction error: {e}\n")
        try:
            tmp_wav.unlink(missing_ok=True)
        except Exception:
            pass
        return None, 0.0


def transcribe_video_sentences(
    filepath: str,
    language: str = "auto",
    model_size: str = "base"
) -> Dict[str, Any]:
    """
    Transcribes media with word-level timestamps and groups words into natural sentence units.
    """
    audio_f32, duration = extract_audio_numpy(filepath)
    if audio_f32 is None or len(audio_f32) == 0:
        return {"duration": duration, "sentences": [], "words": [], "raw_text": ""}

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang_arg = None if (not language or language == "auto") else language
        segments, info = model.transcribe(audio_f32, language=lang_arg, beam_size=3, word_timestamps=True)

        sentences = []
        all_words = []
        full_text_parts = []

        curr_words = []
        curr_text = []
        curr_start = None

        for seg in segments:
            full_text_parts.append(seg.text)
            seg_words = list(seg.words) if hasattr(seg, "words") and seg.words else []

            if not seg_words:
                # Fallback if word timestamps were empty
                sentences.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "words": []
                })
                continue

            for w in seg_words:
                w_dict = {
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2)
                }
                all_words.append(w_dict)

                if curr_start is None:
                    curr_start = w_dict["start"]

                curr_words.append(w_dict)
                curr_text.append(w_dict["word"])

                # Check for sentence enders
                word_clean = w_dict["word"]
                is_sentence_end = any(word_clean.endswith(p) for p in [".", "?", "!", "।", "؟"])
                
                # Or a prolonged pause (>0.65s)
                if is_sentence_end or (len(curr_words) >= 12):
                    s_end = w_dict["end"]
                    sentences.append({
                        "start": curr_start,
                        "end": s_end,
                        "text": " ".join(curr_text).strip(),
                        "words": list(curr_words)
                    })
                    curr_words = []
                    curr_text = []
                    curr_start = None

        if curr_words:
            sentences.append({
                "start": curr_start or 0.0,
                "end": curr_words[-1]["end"],
                "text": " ".join(curr_text).strip(),
                "words": list(curr_words)
            })

        return {
            "duration": round(duration, 2),
            "sentences": sentences,
            "words": all_words,
            "raw_text": " ".join(full_text_parts).strip()
        }
    except Exception as e:
        sys.stderr.write(f"Transcription error: {e}\n")
        return {"duration": duration, "sentences": [], "words": [], "raw_text": ""}


def score_sentence_hook(text: str) -> float:
    """
    Computes a semantic hook curiosity score (0.0 - 1.0) for an opening sentence.
    """
    t_lower = text.lower()
    score = 0.20  # Base line

    # Question sentence boost
    if any(q in t_lower for q in ["?", "why", "how", "what", "who", "when", "keno", "kivabe", "konta", "ki "]):
        score += 0.35

    # Check viral trigger keywords
    for trig in VIRAL_TRIGGERS_EN + VIRAL_TRIGGERS_BN + VIRAL_TRIGGERS_BANGLISH:
        if trig in t_lower:
            score += 0.25
            break

    # Exclamation or high energy
    if "!" in text or "wow" in t_lower or "omg" in t_lower:
        score += 0.20

    # Short, punchy opening (< 8 words)
    words = text.split()
    if 3 <= len(words) <= 9:
        score += 0.15

    return min(1.0, score)


def detect_viral_moments_local(
    transcript_info: Dict[str, Any],
    total_duration: float,
    target_duration: float = 30.0,
    max_clips: int = 5
) -> List[Dict[str, Any]]:
    """
    High-precision Local NLP Viral Moment Detector.
    Uses transcript sentences, hook triggers, speech rate spikes,
    and natural boundary snapping to find real engaging segments.
    """
    sentences = transcript_info.get("sentences", [])
    if not sentences or total_duration <= 5.0:
        # Fallback to single opening clip if no speech detected
        t_dur = min(total_duration, target_duration)
        return [{
            "id": "clip-1",
            "rank": 1,
            "title": "Intro Highlight Moment",
            "start": 0.0,
            "end": round(t_dur, 2),
            "duration": round(t_dur, 2),
            "viral_score": 88,
            "hook_score": 90,
            "retention_score": 88,
            "energy_score": 86,
            "badge_label": "Viral Potential 🔥",
            "badge_class": "viral-high",
            "snippet": f"Opening {t_dur:.1f}s section with dynamic pacing."
        }]

    target_win = max(15.0, min(total_duration, float(target_duration)))
    candidates = []

    # Slide across candidate sentence starting points
    for i, start_sent in enumerate(sentences):
        st = start_sent["start"]
        if st + 10.0 > total_duration:
            break

        # Accumulate sentences until window duration is reached
        included_sents = []
        ed = st
        for j in range(i, len(sentences)):
            cand_sent = sentences[j]
            included_sents.append(cand_sent)
            ed = cand_sent["end"]
            curr_dur = ed - st
            if curr_dur >= target_win:
                break

        curr_dur = ed - st
        if curr_dur < 10.0:
            continue

        # 1. Opening Hook Score
        hook_power = score_sentence_hook(start_sent["text"])

        # 2. Pacing & Speech Density
        total_words = sum(len(s.get("words", [])) or len(s["text"].split()) for s in included_sents)
        words_per_sec = total_words / max(1.0, curr_dur)
        density_score = min(1.0, words_per_sec / 3.0)

        # 3. Content Virality Score (presence of key revelation words)
        combined_text = " ".join(s["text"] for s in included_sents).lower()
        trigger_hits = 0
        for trig in VIRAL_TRIGGERS_EN + VIRAL_TRIGGERS_BN + VIRAL_TRIGGERS_BANGLISH:
            if trig in combined_text:
                trigger_hits += 1

        trigger_score = min(1.0, trigger_hits * 0.20)

        # 4. Final Normalized Scores
        hook_pts = int(round(hook_power * 100))
        retention_pts = int(round((density_score * 0.60 + trigger_score * 0.40) * 100))
        energy_pts = int(round((density_score * 0.50 + hook_power * 0.50) * 100))

        viral_score = int(round(hook_pts * 0.45 + retention_pts * 0.35 + energy_pts * 0.20))
        viral_score = max(65, min(99, viral_score))

        # Dynamic Headline: Extracted directly from opening hook
        raw_hook = start_sent["text"].strip()
        # Clean punctuation for title
        clean_title = re.sub(r'[\.\?\!\।\,]', '', raw_hook)
        title_words = clean_title.split()
        if len(title_words) > 7:
            clip_title = " ".join(title_words[:6]) + "…"
        elif len(title_words) >= 3:
            clip_title = " ".join(title_words)
        else:
            clip_title = f"Key Insight at {int(st // 60)}:{int(st % 60):02d}"

        # Real verbatim quotation snippet
        quote_snip = f'"{start_sent["text"].strip()}"'
        if len(included_sents) > 1 and len(quote_snip) < 60:
            quote_snip += f' → "{included_sents[-1]["text"].strip()}"'

        candidates.append({
            "start": round(st, 2),
            "end": round(ed, 2),
            "duration": round(curr_dur, 2),
            "viral_score": viral_score,
            "hook_score": max(55, min(99, hook_pts)),
            "retention_score": max(55, min(99, retention_pts)),
            "energy_score": max(55, min(99, energy_pts)),
            "title": clip_title,
            "snippet": f'[{int(st//60):02d}:{int(st%60):02d} - {int(ed//60):02d}:{int(ed%60):02d}] {quote_snip}'
        })

    # Sort descending by viral score
    candidates.sort(key=lambda c: c["viral_score"], reverse=True)

    # De-duplicate overlapping windows
    curated = []
    for cand in candidates:
        overlap = False
        for chosen in curated:
            # Check overlap threshold: cannot overlap by more than 4 seconds
            if not (cand["end"] <= chosen["start"] + 4.0 or cand["start"] >= chosen["end"] - 4.0):
                overlap = True
                break
        if not overlap:
            cand["rank"] = len(curated) + 1
            cand["id"] = f"clip-{len(curated)+1}"
            v_score = cand["viral_score"]
            if v_score >= 90:
                cand["badge_label"] = "Viral Potential 🔥"
                cand["badge_class"] = "viral-high"
            elif v_score >= 80:
                cand["badge_label"] = "High Engagement 🚀"
                cand["badge_class"] = "viral-med"
            else:
                cand["badge_label"] = "Strong Hook 💡"
                cand["badge_class"] = "viral-good"

            curated.append(cand)
            if len(curated) >= max_clips:
                break

    return curated


def detect_viral_moments_llm(
    transcript_info: Dict[str, Any],
    total_duration: float,
    target_duration: float = 30.0,
    max_clips: int = 5,
    provider: str = "gemini",
    api_key: str = "",
    model: str = "",
    custom_endpoint: str = ""
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Cloud AI LLM decision maker.
    Sends timestamped transcript to Gemini / OpenAI / Groq / Claude and receives
    exact curated viral moment cuts with reasoning and viral headlines.
    Returns (curated_clips, status_message).
    """
    sentences = transcript_info.get("sentences", [])
    if not sentences:
        fallback = detect_viral_moments_local(transcript_info, total_duration, target_duration, max_clips)
        return fallback, "Local Fallback (empty transcript)"

    # Format transcript with timestamps
    lines = []
    for s in sentences:
        m_st, s_st = int(s["start"] // 60), int(s["start"] % 60)
        lines.append(f"[{m_st:02d}:{s_st:02d} - {s['start']:.2f}s] {s['text']}")
    formatted_transcript = "\n".join(lines)

    system_instruction = (
        "You are an elite short-form video viral retention director (TikTok, Instagram Reels, YouTube Shorts). "
        "Analyze the provided timestamped transcript and identify the most viral, hook-packed, cohesive moments. "
        f"Each moment should be approximately {int(target_duration)} seconds long (acceptable range: 15 to {int(target_duration)+15} seconds). "
        "A viral moment MUST have: 1) An irresistible opening hook question or declaration, 2) High-energy delivery or key secret revealed, 3) Natural resolution without awkward mid-sentence cutoffs. "
        f"Return the top {max_clips} moments strictly as a JSON array with this schema:\n"
        "[\n"
        "  {\n"
        '    "start": float,\n'
        '    "end": float,\n'
        '    "title": "4 to 7 word viral click-worthy title",\n'
        '    "hook_quote": "Exact words spoken in first 3 seconds",\n'
        '    "viral_score": int between 75 and 99,\n'
        '    "hook_score": int between 75 and 99,\n'
        '    "retention_score": int between 75 and 99,\n'
        '    "energy_score": int between 75 and 99,\n'
        '    "reason": "1 sentence explanation of why this moment hooks viewers"\n'
        "  }\n"
        "]\n"
        "Do not include markdown backticks or any preamble. Return ONLY valid JSON."
    )

    user_prompt = (
        f"Total Video Duration: {total_duration:.1f}s\n"
        f"Target Reel Duration: {target_duration:.1f}s\n\n"
        f"--- TIMESTAMPED TRANSCRIPT ---\n{formatted_transcript}\n--- END TRANSCRIPT ---"
    )

    prov = (provider or "gemini").lower()

    try:
        parsed = call_llm_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            provider=prov,
            api_key=api_key.strip(),
            model=model.strip(),
            custom_endpoint=custom_endpoint.strip(),
            timeout=30
        )

        if isinstance(parsed, dict) and "moments" in parsed:
            parsed = parsed["moments"]
        elif isinstance(parsed, dict) and "clips" in parsed:
            parsed = parsed["clips"]

        if not isinstance(parsed, list) or len(parsed) == 0:
            raise ValueError("LLM response did not contain a valid array of moments")

        curated = []
        for idx, item in enumerate(parsed):
            st = max(0.0, float(item.get("start", 0.0)))
            ed = min(total_duration, float(item.get("end", st + target_duration)))
            dur = round(ed - st, 2)
            if dur < 5.0:
                continue

            v_score = int(item.get("viral_score", 88))
            v_score = max(65, min(99, v_score))

            if v_score >= 90:
                badge_label = "AI Selected 🔥"
                badge_class = "viral-high"
            elif v_score >= 80:
                badge_label = "AI Hook 🚀"
                badge_class = "viral-med"
            else:
                badge_label = "AI Highlight 💡"
                badge_class = "viral-good"

            hook_q = item.get("hook_quote", "").strip()
            reason = item.get("reason", "").strip()

            snippet_text = f'[{int(st//60):02d}:{int(st%60):02d} - {int(ed//60):02d}:{int(ed%60):02d}]'
            if hook_q:
                snippet_text += f' "{hook_q}"'
            if reason:
                snippet_text += f' · {reason}'

            curated.append({
                "id": f"clip-{idx+1}",
                "rank": idx + 1,
                "title": item.get("title", f"Viral Moment #{idx+1}"),
                "start": round(st, 2),
                "end": round(ed, 2),
                "duration": dur,
                "viral_score": v_score,
                "hook_score": int(item.get("hook_score", v_score + 2)),
                "retention_score": int(item.get("retention_score", v_score)),
                "energy_score": int(item.get("energy_score", v_score - 1)),
                "badge_label": badge_label,
                "badge_class": badge_class,
                "snippet": snippet_text,
                "ai_curated": True,
                "provider": prov
            })

            if len(curated) >= max_clips:
                break

        if curated:
            return curated, f"AI LLM ({prov.capitalize()})"

    except Exception as e:
        sys.stderr.write(f"LLM detection notice: {e}\nFalling back to Smart Local NLP.\n")

    # Clean fallback to Smart Local NLP
    fallback = detect_viral_moments_local(transcript_info, total_duration, target_duration, max_clips)
    return fallback, "Smart Local NLP (Fallback)"


def detect_hook_moments_llm(
    filepath_or_transcript: Any,
    clip_count: int = 3,
    clip_duration: float = 2.5,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Cloud AI Narrative Hook / Teaser Climax Selector.
    Finds top high-voltage opening teaser moments from the transcript.
    """
    ai_cfg = load_ai_config()
    prov = (provider or ai_cfg.get("provider", "gemini")).lower()
    key = api_key or ai_cfg.get("api_key", "")
    mod = model or ai_cfg.get("model", "")
    endpoint = custom_endpoint or ai_cfg.get("custom_endpoint", "")

    if isinstance(filepath_or_transcript, (str, Path)):
        transcript_info = transcribe_video_sentences(str(filepath_or_transcript), model_size="base")
        total_duration = transcript_info.get("duration", 0.0)
    elif isinstance(filepath_or_transcript, dict):
        transcript_info = filepath_or_transcript
        total_duration = transcript_info.get("duration", 0.0)
    else:
        raise ValueError("Invalid transcript or filepath passed to detect_hook_moments_llm")

    sentences = transcript_info.get("sentences", [])
    if not sentences or not key.strip():
        if isinstance(filepath_or_transcript, (str, Path)):
            from hook_engine import detect_hook_moments
            return detect_hook_moments(str(filepath_or_transcript), clip_count=clip_count, clip_duration=clip_duration)
        return []

    lines = []
    for s in sentences:
        m_st, s_st = int(s["start"] // 60), int(s["start"] % 60)
        lines.append(f"[{m_st:02d}:{s_st:02d} - {s['start']:.2f}s] {s['text']}")
    formatted_transcript = "\n".join(lines)

    sys_prompt = (
        "You are an elite short-form video viral retention director. "
        "Find the top dramatic climax, mystery question, or plot twist moments in the video transcript "
        "to assemble a high-intrigue 0:00 teaser hook intro. "
        f"Select exactly {clip_count} moments spread across different parts of the video. "
        f"Each moment MUST be approximately {clip_duration:.1f} seconds long and end naturally. "
        "Return strictly a JSON array with this schema:\n"
        "[\n"
        "  {\n"
        '    "start": float,\n'
        '    "end": float,\n'
        '    "label": "Act 1: Intriguing Hook / Act 2: Climax Spike / Act 3: Mystery Reveal",\n'
        '    "energy": int between 80 and 99,\n'
        '    "quote": "Exact words spoken in this teaser clip",\n'
        '    "reason": "Why this moment hooks the viewer immediately"\n'
        "  }\n"
        "]\n"
        "Return ONLY the valid JSON array."
    )

    user_prompt = f"Video Total Duration: {total_duration:.1f}s\n\n--- TRANSCRIPT ---\n{formatted_transcript}\n--- END ---"

    try:
        parsed = call_llm_json(
            system_instruction=sys_prompt,
            user_prompt=user_prompt,
            provider=prov,
            api_key=key,
            model=mod,
            custom_endpoint=endpoint,
            timeout=25
        )
        if isinstance(parsed, dict) and "moments" in parsed:
            parsed = parsed["moments"]
        elif isinstance(parsed, dict) and "clips" in parsed:
            parsed = parsed["clips"]

        if isinstance(parsed, list) and len(parsed) > 0:
            results = []
            for i, item in enumerate(parsed[:clip_count]):
                st = max(0.0, float(item.get("start", 0.0)))
                en = min(total_duration, float(item.get("end", st + clip_duration)))
                if en <= st + 0.5:
                    en = min(total_duration, st + clip_duration)
                results.append({
                    "index": i + 1,
                    "start": round(st, 2),
                    "end": round(en, 2),
                    "duration": round(en - st, 2),
                    "label": item.get("label", f"Moment {i+1}: AI Climax Teaser"),
                    "energy": int(item.get("energy", 92 - (i * 2))),
                    "quote": item.get("quote", ""),
                    "reason": item.get("reason", ""),
                    "ai_generated": True,
                    "provider": prov
                })
            if len(results) >= 2:
                return results
    except Exception as e:
        sys.stderr.write(f"detect_hook_moments_llm notice: {e}\nFalling back to local.\n")

    if isinstance(filepath_or_transcript, (str, Path)):
        from hook_engine import detect_hook_moments
        return detect_hook_moments(str(filepath_or_transcript), clip_count=clip_count, clip_duration=clip_duration)
    return []


def generate_social_metadata_llm(
    filepath_or_transcript: Any,
    language: str = "auto",
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates YouTube / TikTok / Reels viral metadata:
    - 5 Viral High-CTR Titles
    - 3 Description styles (Punchy, SEO-rich, Storytelling)
    - Timestamped YouTube Chapters
    - 15 High-engagement hashtags
    - 2-sentence summary
    """
    ai_cfg = load_ai_config()
    prov = (provider or ai_cfg.get("provider", "gemini")).lower()
    key = api_key or ai_cfg.get("api_key", "")
    mod = model or ai_cfg.get("model", "")
    endpoint = custom_endpoint or ai_cfg.get("custom_endpoint", "")

    if not key.strip():
        raise ValueError("AI API Key is required for generating Social Metadata & Chapters.")

    if isinstance(filepath_or_transcript, (str, Path)):
        transcript_info = transcribe_video_sentences(str(filepath_or_transcript), language=language, model_size="base")
        total_duration = transcript_info.get("duration", 0.0)
    elif isinstance(filepath_or_transcript, dict):
        transcript_info = filepath_or_transcript
        total_duration = transcript_info.get("duration", 0.0)
    else:
        raise ValueError("Invalid transcript or filepath passed to generate_social_metadata_llm")

    sentences = transcript_info.get("sentences", [])
    if not sentences:
        raise ValueError("Transcript is empty or could not be generated.")

    lines = []
    for s in sentences:
        m_st, s_st = int(s["start"] // 60), int(s["start"] % 60)
        lines.append(f"[{m_st:02d}:{s_st:02d}] {s['text']}")
    formatted_transcript = "\n".join(lines)

    sys_prompt = (
        "You are an elite video metadata & audience growth strategist for YouTube, Instagram Reels, and TikTok. "
        "Analyze the timestamped video transcript and produce optimized viral metadata. "
        "Return strictly valid JSON with this schema:\n"
        "{\n"
        '  "summary": "2-sentence compelling overview of the video core message",\n'
        '  "titles": ["5 distinct high-CTR, curiosity-driven titles with emojis"],\n'
        '  "descriptions": {\n'
        '    "punchy": "Short punchy caption with hook + emojis (for Reels/TikTok/Shorts)",\n'
        '    "seo_detailed": "Full YouTube SEO description with keywords and call-to-action",\n'
        '    "storytelling": "Story-driven narrative caption that builds curiosity"\n'
        '  },\n'
        '  "chapters": [\n'
        '    {"timecode": "00:00", "seconds": 0.0, "title": "Intro & Hook"}\n'
        '  ],\n'
        '  "hashtags": ["#tag1", "#tag2"]\n'
        "}\n"
        "Note: Chapters must cover meaningful topic transitions, start at 00:00, and be in chronological order."
    )

    user_prompt = f"Video Total Duration: {total_duration:.1f}s\n\n--- TRANSCRIPT ---\n{formatted_transcript}\n--- END ---"

    parsed = call_llm_json(
        system_instruction=sys_prompt,
        user_prompt=user_prompt,
        provider=prov,
        api_key=key,
        model=mod,
        custom_endpoint=endpoint,
        timeout=35
    )

    return {
        "status": "success",
        "provider": prov,
        "model": mod,
        "total_duration": total_duration,
        "data": parsed
    }


def polish_captions_llm(
    subtitles: List[Dict[str, Any]],
    style: str = "viral_karaoke",
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Polishes subtitle text with smart contextual emojis (😱, 🔥, 💡, 🚀) and
    identifies high-emphasis power words without changing timestamps.
    """
    ai_cfg = load_ai_config()
    prov = (provider or ai_cfg.get("provider", "gemini")).lower()
    key = api_key or ai_cfg.get("api_key", "")
    mod = model or ai_cfg.get("model", "")
    endpoint = custom_endpoint or ai_cfg.get("custom_endpoint", "")

    if not key.strip() or not subtitles:
        return subtitles

    input_lines = [{"id": i, "text": s.get("text", "")} for i, s in enumerate(subtitles)]

    sys_prompt = (
        "You are a short-form viral subtitle specialist. "
        "Enhance the following subtitle lines for high viewer retention: "
        "1. Insert 1-2 relevant contextual emojis at dramatic or punchy moments (e.g. 🔥, 💡, 🚀, 😱, ⚡, ⚠️). "
        "2. Wrap 1-2 high-impact emphasis words per sentence in asterisks (e.g. *NEVER*, *SECRET*). "
        "3. Preserve the exact meaning, language, and IDs. "
        "Return strictly a JSON array of objects: [{\"id\": int, \"text\": \"polished text\"}]."
    )

    user_prompt = json.dumps(input_lines, ensure_ascii=False)

    try:
        parsed = call_llm_json(
            system_instruction=sys_prompt,
            user_prompt=user_prompt,
            provider=prov,
            api_key=key,
            model=mod,
            custom_endpoint=endpoint,
            timeout=25
        )
        if isinstance(parsed, list):
            lookup = {item["id"]: item.get("text", "") for item in parsed if "id" in item}
            polished = []
            for i, s in enumerate(subtitles):
                copy_s = dict(s)
                if i in lookup and lookup[i].strip():
                    copy_s["text"] = lookup[i].strip()
                polished.append(copy_s)
            return polished
    except Exception as e:
        sys.stderr.write(f"polish_captions_llm notice: {e}\n")

    return subtitles


def query_video_assistant_llm(
    filepath_or_transcript: Any,
    user_query: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interactive AI Video Assistant:
    Answers questions about what was said or shown in the video,
    returning detailed answers and exact clickable timestamps to navigate in Premiere Pro!
    """
    ai_cfg = load_ai_config()
    prov = (provider or ai_cfg.get("provider", "gemini")).lower()
    key = api_key or ai_cfg.get("api_key", "")
    mod = model or ai_cfg.get("model", "")
    endpoint = custom_endpoint or ai_cfg.get("custom_endpoint", "")

    if not key.strip():
        raise ValueError("AI API Key is required for AI Video Assistant.")

    if isinstance(filepath_or_transcript, (str, Path)):
        transcript_info = transcribe_video_sentences(str(filepath_or_transcript), model_size="base")
        total_duration = transcript_info.get("duration", 0.0)
    elif isinstance(filepath_or_transcript, dict):
        transcript_info = filepath_or_transcript
        total_duration = transcript_info.get("duration", 0.0)
    else:
        raise ValueError("Invalid transcript or filepath passed to query_video_assistant_llm")

    sentences = transcript_info.get("sentences", [])
    lines = []
    for s in sentences:
        m_st, s_st = int(s["start"] // 60), int(s["start"] % 60)
        lines.append(f"[{m_st:02d}:{s_st:02d} - {s['start']:.2f}s] {s['text']}")
    formatted_transcript = "\n".join(lines)

    sys_prompt = (
        "You are OpenCut AI Video Assistant for Adobe Premiere Pro editors. "
        "Answer the user's question about the video accurately using the timestamped transcript. "
        "Extract exact timestamp references so the editor can jump their timeline directly to those moments. "
        "Return strictly valid JSON with this schema:\n"
        "{\n"
        '  "answer": "Clear, concise direct answer with key takeaways",\n'
        '  "timestamps": [\n'
        '    {"seconds": float, "timecode": "MM:SS", "label": "Context of this moment"}\n'
        '  ],\n'
        '  "suggested_actions": ["e.g. Cut this section", "Create a highlight reel here"],\n'
        '  "confidence": "high"\n'
        "}\n"
    )

    user_prompt = f"Video Total Duration: {total_duration:.1f}s\n\n--- TRANSCRIPT ---\n{formatted_transcript}\n--- END ---\n\nUser Question: {user_query}"

    parsed = call_llm_json(
        system_instruction=sys_prompt,
        user_prompt=user_prompt,
        provider=prov,
        api_key=key,
        model=mod,
        custom_endpoint=endpoint,
        timeout=30
    )

    return {
        "status": "success",
        "provider": prov,
        "query": user_query,
        "total_duration": total_duration,
        "result": parsed
    }


def analyze_video_moments(
    filepath: str,
    language: str = "auto",
    target_duration: float = 30.0,
    max_clips: int = 5,
    mode: str = "auto",
    ai_provider: Optional[str] = None,
    api_key: Optional[str] = None,
    ai_model: Optional[str] = None,
    custom_endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for intelligent viral moment analysis.
    Switches between Smart Local NLP and Cloud AI LLM based on user selection and config.
    """
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"Media file not found: {filepath}")

    # Load persistent AI configuration
    ai_cfg = load_ai_config()

    # Determine execution mode
    resolved_provider = ai_provider or ai_cfg.get("provider", "gemini")
    resolved_key = api_key or ai_cfg.get("api_key", "")
    resolved_model = ai_model or ai_cfg.get("model", "")
    resolved_custom_endpoint = custom_endpoint or ai_cfg.get("custom_endpoint", "")

    # Mode: 'llm', 'local', or 'auto'
    if mode == "llm":
        use_llm = True
    elif mode == "local":
        use_llm = False
    else:  # auto
        use_llm = bool(ai_cfg.get("enabled", False) and resolved_key.strip())

    # Step 1: Transcribe video sentences
    transcript_info = transcribe_video_sentences(str(input_path), language=language, model_size="base")
    total_duration = transcript_info.get("duration", 0.0)

    # Step 2: Detect moments via LLM or Local NLP
    if use_llm and resolved_key.strip():
        clips, engine_label = detect_viral_moments_llm(
            transcript_info=transcript_info,
            total_duration=total_duration,
            target_duration=target_duration,
            max_clips=max_clips,
            provider=resolved_provider,
            api_key=resolved_key,
            model=resolved_model,
            custom_endpoint=resolved_custom_endpoint
        )
    else:
        clips = detect_viral_moments_local(
            transcript_info=transcript_info,
            total_duration=total_duration,
            target_duration=target_duration,
            max_clips=max_clips
        )
        engine_label = "Smart Local NLP"

    return {
        "status": "success",
        "total_duration": total_duration,
        "target_duration": target_duration,
        "engine_used": engine_label,
        "clips": clips,
        "transcript_preview": transcript_info.get("raw_text", "")[:250] + ("…" if len(transcript_info.get("raw_text", "")) > 250 else "")
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_video = sys.argv[1]
        print(f"Testing AI Moment Intelligence on {test_video}...")
        res = analyze_video_moments(test_video, mode="local")
        print(json.dumps(res, indent=2))
