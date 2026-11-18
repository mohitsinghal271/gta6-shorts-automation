# 🌴 GTA 6 AI YouTube Shorts Automation Agent

An autonomous, end-to-end AI agent that transforms raw GTA 6 gameplay footage into professional, high-CTR vertical (9:16) YouTube Shorts with multilingual voiceovers, dynamic animated karaoke captions, intelligent cropping, and automated YouTube Data API publishing.

Built **100% on free and open-source technologies**. Zero paid video editing APIs, zero paid cloud services.

---

## 🌟 Key Features

1. **Dual Gameplay Ingestion Modes**:
   - **Mode A (User-Provided Footage)**: Drag-and-drop or batch folder monitoring (`input/` folder) for MP4, MOV, MKV, AVI, and WebM videos.
   - **Mode B (Authorized Source Discovery)**: Strict copyright and permission verification engine supporting Creative Commons (CC-BY), official publisher press kits, and verified creator submissions. Never bypasses DRM or republishes uncredited footage.

2. **Multi-Modal AI Analysis & Highlight Detection**:
   - Frame-difference motion dynamics and visual excitement scoring.
   - Audio RMS energy envelope analysis (detects crashes, sirens, engine revs, gunshots, explosions).
   - Hook potential scoring (evaluates the first 3.5 seconds) and ending resolution quality.
   - Non-Maximum Suppression (temporal IoU) to eliminate redundant, repetitive clips.

3. **Professional 9:16 Vertical Video Engine (FFmpeg)**:
   - **Blurred Background Stack**: 16:9 gameplay crisp in foreground, blurred and darkened in 9:16 background to eliminate black bars.
   - **Intelligent Center Crop**: Smooth pan/crop keeping the action centered.
   - **Cinematic Templates**: `cinematic_hype` (Vice City neon contrast boost), `action_fast` (high saturation & dynamic zoom), `story_npc` (natural cinematic), `funny_moments` (vibrant comedy).

4. **Multilingual Voiceover & Dynamic Subtitles**:
   - Supports **Hindi** (Devanagari script), **English** (energetic gaming commentary), and **Hinglish** (authentic Indian gaming slang).
   - Powered by `edge-tts` (Microsoft neural voices) with automatic offline fallback to Windows SAPI speech synthesis.
   - Dynamic **Karaoke-style word highlighting** (ASS subtitles) with yellow accent highlighting, safe-zone margin placement (Y: 72%), and full Unicode support.
   - Option for gameplay-only audio without commentary.

5. **AI Content & Metadata Generation**:
   - 3 high-CTR title variations per clip (Curiosity Hook, High-Action, Viral Statement) + recommended best title.
   - Rich descriptions with timestamps, chapters, attribution credits, and fair-use disclaimers.
   - High-volume search tags and hashtags (`#GTA6`, `#GTA6Shorts`, `#Gaming`).
   - Thumbnail visual concept description and pinned comment prompt to boost user engagement.

6. **YouTube Automation (Data API v3)**:
   - Official Google OAuth 2.0 flow with token persistence.
   - Resumable chunked upload with exponential backoff retry.
   - Scheduled publishing and privacy status controls (`private`, `unlisted`, `public`).
   - Human-in-the-loop review workflow: clips are held in `pending_review` until explicitly approved.
   - Built-in dry-run simulation mode for development and testing without live credentials.

7. **Semantic AI Gameplay Analysis (Priority 2)**:
   - Intelligent 3-point keyframe extraction (Hook, Actual Motion/Audio Peak Action Moment, Climax/Resolution).
   - Vision Language Model (Moondream / Qwen Vision / Ollama) multimodal scoring:
     - **Humor Score** (glitches, unexpected physics, comedic moments)
     - **Stunt Score** (high-speed jumps, acrobatic driving, aerial maneuvers)
     - **Cinematic Score** (lighting, camera framing, neon Vice City atmosphere)
     - **Composite Engagement Formula**: `0.40 * Stunt + 0.35 * Humor + 0.25 * Cinematic` (Neutral fallback: 54.25)
   - Factual neutral fallbacks when VLM is unavailable ("GTA 6 gameplay sequence" without fake event hallucinations).
   - Highlight Ranker integration blending motion dynamics, audio energy, and semantic composite scores.
   - Contextual commentary generator utilizing event summaries, entertainment reasoning, and viral hooks.

8. **Extensible Multi-Game Presets**:
   - Pre-configured for **GTA 6** (Vice City neon vibe, crime tags).
   - Instant extensibility for **GTA 5**, **Red Dead Redemption 2**, **Minecraft**, and custom games via `config.py`.

---

## 🏗️ Architecture & Directory Structure

```
GTA_6/
├── app.py                     # Streamlit Interactive Web Dashboard
├── web_app.py                 # Standalone FastAPI + HTML5/Tailwind Dashboard (Zero extra install)
├── cli.py                     # Headless Automation & Batch CLI Runner
├── config.py                  # Central configuration, paths, and game presets
├── requirements.txt           # Project dependencies
├── README.md                  # Comprehensive documentation
├── .env.example               # Environment variable templates
├── database/
│   ├── schema.sql             # Relational SQLite schema (sources, gameplay, clips, metadata, history)
│   └── db.py                  # Database access layer (CRUD & KPI statistics)
├── modules/
│   ├── __init__.py
│   ├── gameplay_ingestion.py  # SHA256 hashing, video probing, folder watcher
│   ├── source_discovery.py    # Mode B license validator and legal attribution generator
│   ├── scene_detector.py      # Frame sampling & scene cut detector
│   ├── video_analyzer.py      # Motion dynamics, audio RMS, hook & unpredictability scorer
│   ├── semantic_analyzer.py   # Semantic AI Gameplay Analysis (VLM + Keyframes + Scoring)
│   ├── highlight_ranker.py    # Non-Maximum Suppression (temporal IoU) highlight ranker
│   ├── clip_generator.py      # Frame-accurate subclip extraction via FFmpeg
│   ├── voice_generator.py     # Multilingual gaming commentary (Hindi/English/Hinglish)
│   ├── subtitle_generator.py  # SRT & ASS dynamic karaoke subtitle generator
│   ├── audio_processor.py     # Multi-track mixing with sidechain voiceover ducking
│   ├── video_editor.py        # 9:16 vertical transformation, color grading, subtitle burn
│   ├── metadata_generator.py  # High-CTR YouTube titles, SEO tags, descriptions, pinned comments
│   ├── youtube_uploader.py    # Official YouTube Data API v3 uploader & simulation engine
│   ├── duplicate_detector.py  # Duplicate footage & upload prevention
│   └── pipeline.py            # Master workflow orchestrator
├── input/                     # Watched directory for raw gameplay footage
├── output/
│   ├── candidates/            # Extracted horizontal candidate clips
│   └── final/                 # Rendered 1080x1920 vertical Shorts ready for YouTube
├── assets/
│   ├── voiceovers/            # Generated speech audio files
│   └── subtitles/             # Generated SRT and ASS subtitle files
└── tests/
    ├── test_db.py
    ├── test_ingestion_and_sources.py
    ├── test_scene_and_analysis.py
    ├── test_semantic_analyzer.py
    ├── test_voice_and_subtitles.py
    ├── test_metadata_and_youtube.py
    ├── test_robustness_and_edge_cases.py
    └── test_e2e_pipeline.py
```

---

## ⚡ Quick Start & Usage

### 1. Requirements
- Python 3.10+
- FFmpeg (automatically detected from system PATH or bundled `imageio-ffmpeg`)

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. (Optional) Vision Language Model Setup (Moondream / Ollama)
```bash
# Install Ollama for Windows from https://ollama.com
ollama run moondream
# The semantic analyzer will automatically query http://localhost:11434/api/generate
# If Ollama is offline, the system seamlessly falls back to factual neutral analysis (54.25)
```

### 3. Launch the Web Dashboard

You have two dashboard options:

**Option A: Standalone FastAPI Dashboard (Fastest, zero setup)**:
```bash
python web_app.py
```
Open [http://127.0.0.1:8501](http://127.0.0.1:8501) in your browser.

**Option B: Streamlit Dashboard**:
```bash
streamlit run app.py
```

### 4. Command-Line Interface (CLI)

Run end-to-end processing on any video:
```bash
# Process a video with Hinglish voiceover and cinematic template
python cli.py run-pipeline "input/gta6_gameplay.mp4" --lang hinglish --template cinematic_hype

# Scan input folder for new gameplay
python cli.py scan

# List generated clips
python cli.py list-clips

# Approve a clip
python cli.py approve 1

# Upload approved clip to YouTube (simulation mode by default)
python cli.py upload 1 --privacy private
```

---

## 🎬 Editing Templates

| Template | Cropping Mode | Color Grade | Style |
|---|---|---|---|
| `cinematic_hype` | Blurred 9:16 Stack | Neon Contrast (+18% sat) | High-energy trailer aesthetic |
| `action_fast` | Center Crop | Punchy (+20% sat, +12% cont) | Action-focused, rapid cuts |
| `story_npc` | Blurred 9:16 Stack | Natural Film Grade | Clear dialogue and NPC focus |
| `funny_moments` | Blurred 9:16 Stack | High Saturation (+25% sat) | Comedy & crazy physics |

---

## 🧪 Running the Test Suite

Run the full suite of 35 automated tests:
```bash
python -m unittest discover -s tests -v
```

---

## ⚖️ Legal & Fair Use Guidelines

- **Mode B Compliance**: Only ingest footage with verified Creative Commons or publisher press kit permissions.
- **Fair Use**: Derivative commentary, critique, and reviews of gaming footage are protected under Fair Use laws. All generated metadata includes standard publisher disclaimers.
- **Voice Synthesis**: Voices are generated via synthetic TTS engines; no real creator's voice is cloned without authorization.
