"""
OpenCut AI Agent Skills Engine
Manages autonomous editing skills, custom system prompts, and creator directives.
Skills are stored as Markdown/YAML/JSON files in E:\\autocut\\skills.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

SKILLS_DIR = Path("E:/autocut/skills")
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SKILLS = [
    {
        "id": "youtube_retention_master",
        "name": "YouTube High-Retention Master",
        "category": "editing",
        "description": "Edits long-form videos like MrBeast/Ali Abdaal: fast pacing, hook card within 1s, zoom punch-ins on keywords, subscribe callout at 30%, and dynamic auto-ducked SFX.",
        "enabled": True,
        "system_prompt": (
            "You are an Elite YouTube Video Editor and Creative Director. "
            "Prioritize retention above all: identify the single most gripping hook for the first 3 seconds, "
            "schedule camera punch-in zooms on high-emphasis statements every 8-15 seconds, "
            "place animated motion cards at key topic shifts, and design punchy SFX (whoosh on zooms, impact on hooks)."
        ),
        "guidelines": [
            "Keep intro hook card under 4 seconds",
            "Place camera punch-in zoom at dramatic statements",
            "Insert subscribe card at 25-35% video progress",
            "Choose vibrant yellow/cyan karaoke captions"
        ]
    },
    {
        "id": "viral_reels_shorts",
        "name": "Viral TikTok & Reels Specialist",
        "category": "reels",
        "description": "Specialized in 9:16 vertical short-form: viral question hooks, fast-paced cuts, karaoke typography with emojis, and punchline reaction memes.",
        "enabled": True,
        "system_prompt": (
            "You are an Elite Short-Form Viral Video Director for TikTok, Instagram Reels, and YouTube Shorts. "
            "Find moments with undeniable curiosity gaps, emotional peaks, or controversial statements. "
            "Ensure the opening 2 seconds immediately stop the scroll. Cut all unnecessary pause intervals."
        ),
        "guidelines": [
            "Target 20-45 second optimal duration",
            "Opening must pose a compelling question or revelation",
            "Use split-screen or blurred background for wide footage",
            "Add animated progress bar and top hook card"
        ]
    },
    {
        "id": "educational_tutorial_clean",
        "name": "Clean Educational & Coding Guide",
        "category": "tutorial",
        "description": "Polite, focused, and crisp: subtle 1.12x zooms on code/takeaways, minimal non-distracting sound design, and clean boxed subtitles.",
        "enabled": False,
        "system_prompt": (
            "You are a Professional Technical and Educational Video Editor. "
            "Maintain clarity, elegance, and calm focus. Avoid aggressive jumps or jarring sound effects. "
            "Use subtle punch-ins when key code lines or principles are stated."
        ),
        "guidelines": [
            "Use subtle 112% zoom scales",
            "Minimalist sound design (soft clicks, subtle whooshes)",
            "Boxed dark captions with high contrast",
            "Highlight takeaways and chapter points"
        ]
    },
    {
        "id": "gaming_hyper_energy",
        "name": "Gaming & Stream Climax",
        "category": "gaming",
        "description": "High energy gaming cuts: bass drops on clutches, snap-in pop zooms on screams/kills, and meme GIF overlays on funny fails.",
        "enabled": False,
        "system_prompt": (
            "You are a High-Energy Gaming Content Editor. "
            "Detect epic clutch plays, hilarious fails, loud audio reactions, and hype climaxes. "
            "Use aggressive snap-in zooms, 808 bass drops, and reaction meme inserts."
        ),
        "guidelines": [
            "Aggressive 125% snap-in zooms on peak vocal energy",
            "Bass drop / riser sound design on action build-ups",
            "Insert funny reaction GIF on sudden silences or deaths"
        ]
    }
]


def init_default_skills():
    """Ensure default skills exist on disk."""
    for sk in DEFAULT_SKILLS:
        sk_path = SKILLS_DIR / f"{sk['id']}.json"
        if not sk_path.exists():
            try:
                with open(sk_path, "w", encoding="utf-8") as f:
                    json.dump(sk, f, indent=2)
            except Exception as e:
                sys.stderr.write(f"Notice creating skill {sk['id']}: {e}\n")


# Initialize on import
init_default_skills()


def list_skills() -> List[Dict[str, Any]]:
    """List all available skills from disk."""
    skills = []
    try:
        for f in sorted(SKILLS_DIR.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    skills.append(data)
            except Exception:
                pass
    except Exception as e:
        sys.stderr.write(f"Error listing skills: {e}\n")

    if not skills:
        return DEFAULT_SKILLS
    return skills


def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
    """Get a single skill by ID."""
    sk_path = SKILLS_DIR / f"{skill_id}.json"
    if sk_path.exists():
        try:
            with open(sk_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    for sk in DEFAULT_SKILLS:
        if sk["id"] == skill_id:
            return sk
    return None


def save_skill(skill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a skill."""
    sk_id = skill_data.get("id")
    if not sk_id:
        name = skill_data.get("name", "custom_skill")
        sk_id = "".join([c.lower() if c.isalnum() else "_" for c in name]).strip("_")
        sk_id = f"{sk_id}_{int(time.time())}"
        skill_data["id"] = sk_id

    sk_path = SKILLS_DIR / f"{sk_id}.json"
    with open(sk_path, "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2)

    return skill_data


def delete_skill(skill_id: str) -> bool:
    """Delete a skill file."""
    sk_path = SKILLS_DIR / f"{skill_id}.json"
    if sk_path.exists():
        try:
            os.remove(str(sk_path))
            return True
        except Exception:
            return False
    return False


def get_combined_agent_prompt(custom_override_prompt: Optional[str] = None) -> str:
    """
    Combines enabled skills and custom user prompts into the master system instruction.
    User's custom backend prompt ALWAYS has the highest priority!
    """
    sections = []
    
    # 1. Base Core Capability
    sections.append(
        "You are OpenCut Autonomous AI Video Editor Agent, equipped with Adobe Premiere Pro integration, "
        "faster-whisper transcription, kinetic karaoke typography, and high-retention narrative pacing."
    )

    # 2. Enabled Skills Directives
    skills = list_skills()
    enabled_skills = [s for s in skills if s.get("enabled")]
    if enabled_skills:
        sections.append("\n=== ACTIVE EDITOR SKILLS & DIRECTIVES ===")
        for sk in enabled_skills:
            sections.append(f"[{sk.get('name', 'Skill')}]: {sk.get('system_prompt', '')}")
            if sk.get("guidelines"):
                sections.append("Guidelines: " + "; ".join(sk.get("guidelines", [])))

    # 3. User Custom Backend Prompt (TOP PRIORITY)
    if custom_override_prompt and custom_override_prompt.strip():
        sections.append("\n=== USER CUSTOM CREATIVE DIRECTIVE (HIGHEST PRIORITY) ===")
        sections.append(custom_override_prompt.strip())

    return "\n\n".join(sections)
