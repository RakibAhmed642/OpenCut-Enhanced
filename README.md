<div align="center">

# 🎬 OpenCut Studio (Enhanced Edition)
### Next-Gen Autonomous Video Editing & AI Studio for Adobe Premiere Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Premiere Pro](https://img.shields.io/badge/Adobe%20Premiere%20Pro-2022%20--%202026+-9999FF?logo=adobepremierepro&logoColor=white)](https://www.adobe.com/products/premiere.html)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node: 18+](https://img.shields.io/badge/Node.js-18%2B%20%7C%2020%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Accelerated with CUDA](https://img.shields.io/badge/CUDA-Hardware%20Accelerated-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-zone)

**OpenCut Studio** is an open-source, AI-powered autonomous video editing extension and standalone backend engine designed to supercharge video workflows inside Adobe Premiere Pro. From turning long-form footage into viral **9:16 Shorts/Reels**, auto-generating high-retention **video hooks**, to autonomous **sound design** with dynamic ducking and subtitle generation in **Bangla, English, and 30+ languages**.

[Features](#-key-features) • [Architecture](#-architecture) • [Installation](#-installation--quick-start) • [Configuration](#-configuration) • [License](#-license--attribution)

---

</div>

## 🚀 What's New in this Enhanced Edition?

This edition heavily extends the baseline OpenCut infrastructure with cutting-edge production tools, custom AI pipelines, and a refined, minimal UI:

* 📱 **Autonomous Auto-Reels Engine (9:16):** Transforms horizontal raw footage into vertical viral clips with smart face-centering, multi-segment pacing, and automated viral scoring (65+).
* 🎯 **Smart Auto-Hook Generator:** Automatically identifies the most electrifying statement or moment in your media and crafts a fast-paced introductory hook to retain viewers.
* 🔊 **Content-Aware Sound Design Engine:** Automatically generates and mixes high-fidelity SFX stems (*whooshes, risers, impacts, clicks, drops*) with real-time audio ducking and EBU R128 (-16 LUFS) loudness normalization.
* 🧠 **AI Moment Intelligence (Multi-LLM Integration):** Direct integration with **Gemini, OpenAI, Claude, OpenRouter, and Groq** to evaluate emotional arcs, comedic timing, and viral retention points.
* 🌐 **Global Multilingual & Bengali (Bangla) Whisper Engine:** Full support for `whisper-large-v3`, `turbo`, and `distil-large-v3` with flawless **Bangla Unicode font rendering (`Kalpurush`)** and active karaoke word highlights.
* ⚡ **Hardware Acceleration & GPU Crash Shield:** In-place backend engine patch preventing PyTorch dependency lockups, ensuring 100% stable CUDA acceleration on NVIDIA GTX / RTX systems.
* 🎨 **Clean, Minimal UI/UX Redesign:** Streamlined Premiere Pro CEP interface with balanced typography, fixed dropdown layering (`z-index` contexts), and clutter-free controls.

---

## 🌟 Key Features

### 1. 📱 Auto-Reels & Viral Shorts Creator
* **Smart 9:16 Cropping:** Automatic focus on the active speaker.
* **Dual Detection Modes:** Find highlights using **Transcript Semantic Analysis**, **Visual Emotion Scoring (DeepFace)**, or a weighted blend of both.
* **Direct Premiere Pro Integration:** One-click `Add to Timeline` inserts the finished vertical captioned clip onto your active sequence.

### 2. 🪝 Auto-Hook Engine
* Detects high-energy spikes and key conversational hooks.
* Assembles a 3–8 second retention-grabbing preview at the start of your video with kinetic overlays and whoosh transitions.

### 3. 🎧 Autonomous Sound Design Suite
* **BPT (Beat & Point) Triggering:** Automatically places sound effects precisely at visual cuts, text appearance timestamps, and scene transitions.
* **Stem Generation:** Exports isolated `_sfx_stem.wav` tracks alongside the final render for seamless audio mixing.
* **Intelligent Audio Ducking:** Dynamically reduces background music levels during dialogue (-18 dB to -24 dB) and brings it up during pauses.

### 4. ✂️ The Silencer (Dead-Air & Silence Removal)
* High-precision silence detection with millisecond-accurate boundary padding (`0.08s` word padding to eliminate syllable clipping).
* In-place timeline ripple delete or XML sequence export.

### 5. 💬 Kinetic Karaoke Subtitles
* High-retention word-by-word active karaoke text highlighting.
* Cross-platform font fallback (`Kalpurush` for Bengali, `Nirmala UI` for Indic scripts, `Arial` for Latin).
* Safe margin compliance: Positioned above mobile UI buttons (TikTok, Instagram Reels, YouTube Shorts).

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Adobe Premiere Pro [Adobe Premiere Pro Environment]
        CEP["OpenCut CEP Panel (HTML5 / Modern JS)"]
        JSX["ExtendScript Host Bridge (index.jsx)"]
    end

    subgraph Backend Engines [OpenCut Local AI Services]
        Server["OpenCut Backend Server (Port 5679)"]
        SoundService["AI Studio & Sound Designer (Port 5682)"]
    end

    subgraph AI & Processing Core [Processing Core]
        Whisper["Faster-Whisper (CUDA / CPU)"]
        LLM["AI APIs (Gemini / OpenAI / Groq)"]
        FFmpeg["Bundled FFmpeg & Filter Complex"]
    end

    CEP <-->|REST API + CSRF| Server
    CEP <-->|REST API| SoundService
    CEP <-->|CSInterface EvalScript| JSX
    Server --> Whisper
    Server --> FFmpeg
    SoundService --> LLM
    SoundService --> FFmpeg
    JSX -->|Timeline Ripple / Import| Adobe Premiere Pro
```

---

## 📦 Installation & Quick Start

### Prerequisites
* **Adobe Premiere Pro** (2022 or newer)
* **Windows 10 / 11** (64-bit)
* **Python 3.10+** (Python 3.12 or 3.13 recommended)
* **NVIDIA GPU** with CUDA support (Recommended for faster transcription & AI tools)

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/opencut-studio.git
cd opencut-studio
```

### 2. Extension Installation (Premiere Pro CEP)
1. Enable PlayerDebugMode in Windows Registry (if not already enabled):
   ```powershell
   reg add "HKEY_CURRENT_USER\Software\Adobe\CSXS.11" /v PlayerDebugMode /t REG_SZ /d "1" /f
   ```
2. Link or copy the extension folder:
   ```powershell
   python sync_extension.py
   ```
3. Open Adobe Premiere Pro $\rightarrow$ **Window** $\rightarrow$ **Extensions** $\rightarrow$ **OpenCut**.

### 3. Launch Services
Run the launcher script to start all background services:
```cmd
Start-OpenCut.bat
```
Or start manually via CLI:
```powershell
# Core backend server (Port 5679)
.\server\OpenCut-Server.exe

# AI studio & sound design daemon (Port 5682)
python server\sound_designer_service.py
```

---

## ⚙️ Configuration (`config.yaml`)

Customize all global threshold and styling rules in [`config.yaml`](file:///e:/autocut/config.yaml):

```yaml
# Silence & Trimming
silence:
  noise_threshold_db: -30.0
  min_duration: 0.5
padding:
  word_padding: 0.08      # Preserves starting/trailing syllables
  merge_threshold: 0.15   # Merges micro-cuts

# Kinetic Captions
captions:
  font_name: "Arial"
  font_size: 26
  primary_color: "&H00FFFFFF"      # Crisp White
  highlight_color: "&H0022D3EE"    # Vibrant Cyan/Yellow
  outline_width: 3.5
  margin_v: 180                    # Clear of TikTok/Reels UI buttons

# Audio & Sound Design
rendering:
  target_lufs: -16.0               # EBU R128 standard
  ducking_depth_db: -18.0
```

---

## 🤝 Contributing

Contributions, bug reports, and pull requests are warmly welcomed!
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License & Attribution

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for full details.

### Upstream Attribution:
* Based upon and enhanced from the original open-source **[OpenCut](https://github.com/SysAdminDoc/opencut)** project by **SysAdminDoc**, released under the MIT License.
* Copyright (c) 2025 OpenCut Contributors.
* Copyright (c) 2026 Enhanced OpenCut Studio Contributors.
