# OpenCut Autonomous Video Editing Agent Guidelines

## 1. Project Overview & How to Run
OpenCut is an autonomous, high-precision video editing engine integrated into Adobe Premiere Pro and accessible via CLI, Python API, and Model Context Protocol (MCP) stdio.

### CLI Execution
```powershell
# Run Dry Run (inspect EDL cut list without rendering)
C:\Python313\python.exe E:\autocut\server\pipeline.py "path/to/video.mp4" --dry-run

# Run Full Autonomous Edit with Vertical Mode (1080x1920) and EBU R128 Loudness Normalization
C:\Python313\python.exe E:\autocut\server\pipeline.py "path/to/video.mp4" --vertical --normalize

# Custom config
C:\Python313\python.exe E:\autocut\server\pipeline.py "path/to/video.mp4" --config "E:\autocut\config.yaml"
```

---

## 2. Mandatory Agent Rules

### Rule 1: Always Run `--dry-run` First
Before performing any actual re-encode or modifying timelines, the AI agent **MUST ALWAYS** run the pipeline with `--dry-run` first, inspect `edl.json`, and present the cut list to the user:
- Original duration vs expected duration
- Reduction percentage (time saved)
- Total kept segments vs removed segments (silence, filler words, repeated takes)

### Rule 2: Always Extract and Verify 5 Frames Before Saying "Done"
After every render:
1. Extract 5 evenly spaced frames into `work/<clip_hash>/frames/`.
2. Inspect the frames:
   - Check that captions are not cut off or colliding with UI safe margins.
   - Check that vertical 9:16 crop framing is centered and clean.
   - Ensure there are no black frames or corrupt glitches.
3. Compare the actual rendered duration against the expected duration (`tolerance <= 0.3s`).
4. Only when all 5 frames are visually confirmed and duration is verified may the agent report task completion.

---

## 3. Style & Pipeline Settings (`config.yaml`)

All parameters are configured in [`E:\autocut\config.yaml`](file:///e:/autocut/config.yaml):

### Typography & Captions
- **`font_name`**: `Arial` (Cross-platform standard)
- **`font_size`**: `26` (scaled 2x for 9:16 portrait)
- **`primary_color`**: `&H00FFFFFF` (Crisp white)
- **`highlight_color`**: `&H0022D3EE` (Vibrant cyan/yellow active karaoke highlight)
- **`outline_color`**: `&H000B0D14` (Deep black border)
- **`outline_width`**: `3.5`
- **`shadow_depth`**: `1.5`
- **`alignment`**: `2` (Bottom-center)
- **`margin_v`**: `180` (Safe margin clear of TikTok/Reels UI buttons)

### Cutting & Audio Parameters
- **`silence.noise_threshold_db`**: `-30.0` dB
- **`silence.min_duration`**: `0.5` seconds
- **`padding.word_padding`**: `0.08` seconds (prevents syllable clipping)
- **`padding.merge_threshold`**: `0.15` seconds (merges micro-cuts)
- **`fillers.words`**: Bengali, English, and Banglish filler list (`um`, `uh`, `like`, `you know`, `mane`, `ar`, `hmm`, etc.)
- **`repeated_takes.similarity_threshold`**: `0.75` (keeps the LAST take)
- **`rendering.target_lufs`**: `-16.0` LUFS (EBU R128 / YouTube standard)
- **`qa.duration_tolerance`**: `0.3` seconds

---

## 4. MCP Tools Available for AI Agents
Connect via `C:\Users\h\.gemini\config\mcp_config.json`:
- `opencut_smart_cut`: Runs the 10-step autonomous pipeline on any video.
- `hyperframes_generate_video`: Generates animated motion graphic videos.
- `opencut_sound_design`: Content-aware BPT SFX stems and dynamic audio ducking.
- `opencut_get_timeline_config`: Generates multi-track Premiere Pro timeline structures.

---

## 5. Motion Graphics Creator Framework

Always follow these principles when designing motion graphics, launch promos, animated video overlays, and kinetic typography:

### Modes
1. **Mode A - Launch Promos (From Scratch):** Visual storytelling using sleek glassmorphic UI cards, kinetic typography, 3D camera depth, and smooth scene transitions.
2. **Mode B - Script & Footage Overlays:** Timed word-by-word captions, floating callouts, data badges, and B-roll visual inserts.
3. **Mode C - Master Prompts & Blueprints:** Copy-pasteable motion briefs and high-retention video storyboards.

### The 90% Rule (Master Motion Brief)
Before rendering, always establish:
- **Visual Vibe & Art Direction:** Dark Glassmorphic, Paper Cutout Magazine, Neo-Brutalist, or Apple-style Clean.
- **Palette & Gradients:** Exact hex tokens, multi-stop radial glows, dark high-contrast backgrounds.
- **Texture & Lighting:** SVG turbulence noise film grain (3-6% opacity), ambient glow flares, Z-depth drop shadows.
- **Typography:** Bold display font for hooks, clean geometric sans for UI cards, monospace for stats.
- **Choreography & Easing:** Never use linear easing. Always use snappy cubic-bezier curves (`cubic-bezier(0.34, 1.56, 0.64, 1)` for pops, `cubic-bezier(0.16, 1, 0.3, 1)` for smooth deceleration).

