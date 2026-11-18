"""
GTA 6 AI YouTube Shorts Automation Agent - Configuration Module
"""

import os
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def find_ffmpeg_binary() -> str:
    """
    Locate ffmpeg binary on the system:
    1. Environment variable FFMPEG_PATH
    2. System PATH (shutil.which)
    3. imageio_ffmpeg bundled binary
    """
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path

    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except ImportError:
        pass

    return "ffmpeg"


# Base Paths
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
CANDIDATES_DIR = OUTPUT_DIR / "candidates"
FINAL_DIR = OUTPUT_DIR / "final"
BUFFER_DIR = OUTPUT_DIR / "buffer"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ASSETS_DIR = PROJECT_ROOT / "assets"
BGM_DIR = ASSETS_DIR / "bgm"
SFX_DIR = ASSETS_DIR / "sfx"
FONTS_DIR = ASSETS_DIR / "fonts"
DATABASE_DIR = PROJECT_ROOT / "database"
LOGS_DIR = PROJECT_ROOT / "logs"
DATABASE_PATH = DATABASE_DIR / "gta6_shorts.db"

# Ensure all essential directories exist
for directory in [
    INPUT_DIR,
    OUTPUT_DIR,
    CANDIDATES_DIR,
    FINAL_DIR,
    BUFFER_DIR,
    TEMPLATES_DIR,
    ASSETS_DIR,
    BGM_DIR,
    SFX_DIR,
    FONTS_DIR,
    DATABASE_DIR,
    LOGS_DIR,
]:
    os.makedirs(directory, exist_ok=True)


@dataclass
class VideoSettings:
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    min_clip_duration: float = 15.0
    max_clip_duration: float = 60.0
    target_duration_min: float = 25.0
    target_duration_max: float = 45.0
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "8M"
    crf: int = 18
    preset: str = "fast"
    crop_mode: str = "blurred_background_stack"  # 'blurred_background_stack', 'intelligent_center_crop'
    supported_extensions: List[str] = field(
        default_factory=lambda: [".mp4", ".mov", ".mkv", ".avi", ".webm"]
    )


@dataclass
class AudioSettings:
    gameplay_volume: float = 0.55
    voiceover_volume: float = 1.30
    bgm_volume: float = 0.20
    ducking_ratio: float = 0.25  # Lower gameplay audio to 25% when voiceover is speaking
    sample_rate: int = 44100
    target_lufs: float = -14.0  # YouTube Shorts loudness target


@dataclass
class LanguageVoiceSettings:
    default_language: str = "hinglish"
    supported_languages: List[str] = field(
        default_factory=lambda: ["hindi", "english", "hinglish"]
    )
    voice_map: Dict[str, Dict[str, str]] = field(
        default_factory=lambda: {
            "hindi": {
                "male": "hi-IN-MadhurNeural",
                "female": "hi-IN-SwaraNeural",
                "default": "hi-IN-MadhurNeural",
            },
            "english": {
                "male": "en-US-ChristopherNeural",
                "female": "en-US-JennyNeural",
                "energetic": "en-US-GuyNeural",
                "indian_english": "en-IN-PrabhatNeural",
                "default": "en-US-ChristopherNeural",
            },
            "hinglish": {
                "male": "hi-IN-MadhurNeural",
                "casual": "en-IN-PrabhatNeural",
                "default": "hi-IN-MadhurNeural",
            },
        }
    )


def _env_bool(keys: List[str], default: bool) -> bool:
    for k in keys:
        val = os.environ.get(k)
        if val is not None:
            return val.strip().lower() in ("true", "1", "yes", "on")
    return default


def _env_float(keys: List[str], default: float) -> float:
    for k in keys:
        val = os.environ.get(k)
        if val is not None:
            try:
                return float(val.strip())
            except ValueError:
                pass
    return default


def _env_str(keys: List[str], default: str) -> str:
    for k in keys:
        val = os.environ.get(k)
        if val is not None and val.strip():
            return val.strip()
    return default


@dataclass
class YouTubeSettings:
    client_secrets_file: Path = field(
        default_factory=lambda: Path(os.getenv("YOUTUBE_CLIENT_SECRET_FILE", str(PROJECT_ROOT / "client_secrets.json")))
    )
    token_pickle_file: Path = PROJECT_ROOT / "token.pickle"
    token_json_file: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "YOUTUBE_TOKEN_FILE",
                str(PROJECT_ROOT / "youtube_token.json")
                if (PROJECT_ROOT / "youtube_token.json").exists()
                else str(PROJECT_ROOT / "token.json")
            )
        )
    )
    default_privacy: str = field(
        default_factory=lambda: _env_str(["YOUTUBE_DEFAULT_PRIVACY"], "private")
    )
    category_id: str = "20"  # 20 = Gaming
    auto_publish: bool = field(
        default_factory=lambda: _env_bool(["AUTO_PUBLISH"], False)
    )
    simulate_upload: bool = field(
        default_factory=lambda: _env_bool(["YOUTUBE_UPLOAD_SIMULATION", "YOUTUBE_SIMULATE_UPLOAD", "YOUTUBE_SIMULATION_MODE"], True)
    )
    simulate_discovery: bool = field(
        default_factory=lambda: _env_bool(["LIVESTREAM_DISCOVERY_MOCK", "YOUTUBE_DISCOVERY_MOCK"], True)
    )
    simulate_acquisition: bool = field(
        default_factory=lambda: _env_bool(["FOOTAGE_ACQUISITION_SIMULATION"], True)
    )


@dataclass
class StreamSettings:
    chunk_duration_seconds: float = 12.0
    buffer_retention_chunks: int = 5
    discovery_poll_interval_minutes: int = field(
        default_factory=lambda: int(os.getenv("YOUTUBE_DISCOVERY_POLL_INTERVAL_MINUTES", "30"))
    )
    manual_budget_units: int = 1000
    discovery_cache_ttl_seconds: int = 300
    buffer_dir: Path = BUFFER_DIR


@dataclass
class ResourceLimits:
    max_concurrent_streams: int = 3
    max_concurrent_workers: int = 2
    max_active_candidates: int = 50
    ffmpeg_cpu_threads: int = 4
    max_disk_usage_gb: float = 10.0
    min_disk_free_gb: float = 5.0
    temp_chunk_ttl_minutes: int = 15
    candidate_retention_hours: int = 48



@dataclass
class GameSettings:
    current_game: str = "GTA 6"
    theme: str = "vice_city_action"
    keywords: List[str] = field(
        default_factory=lambda: [
            "GTA 6",
            "Grand Theft Auto VI",
            "Vice City",
            "Lucia",
            "Jason",
            "Leonida",
            "GTA 6 Gameplay",
            "GTA 6 Shorts",
            "GTA 6 Updates",
            "Rockstar Games",
        ]
    )
    # Extensible game presets
    game_presets: Dict[str, Dict] = field(
        default_factory=lambda: {
            "GTA 6": {
                "vibe": "vibrant_neon_crime",
                "hashtags": ["#GTA6", "#GTA6Shorts", "#ViceCity", "#Gaming", "#RockstarGames"],
                "color_grading": {"contrast": 1.08, "saturation": 1.15, "brightness": 0.02},
            },
            "GTA 5": {
                "vibe": "los_santos_heist",
                "hashtags": ["#GTA5", "#GTAV", "#LosSantos", "#GamingShorts"],
                "color_grading": {"contrast": 1.05, "saturation": 1.10, "brightness": 0.0},
            },
            "RDR2": {
                "vibe": "cinematic_wild_west",
                "hashtags": ["#RDR2", "#RedDeadRedemption2", "#ArthurMorgan", "#WesternGaming"],
                "color_grading": {"contrast": 1.10, "saturation": 0.95, "brightness": -0.02},
            },
            "Minecraft": {
                "vibe": "vibrant_block_adventure",
                "hashtags": ["#Minecraft", "#MinecraftShorts", "#MinecraftMemes", "#Gaming"],
                "color_grading": {"contrast": 1.05, "saturation": 1.20, "brightness": 0.03},
            },
        }
    )


@dataclass
class SemanticAnalysisSettings:
    enabled: bool = True
    vlm_provider: str = "moondream"  # 'moondream', 'qwen_vision', 'ollama', 'mock'
    vlm_endpoint: str = field(
        default_factory=lambda: (
            f"{os.environ['OLLAMA_HOST'].rstrip('/')}/api/generate"
            if os.environ.get("OLLAMA_HOST")
            else "http://localhost:11434/api/generate"
        )
    )
    model_name: str = field(
        default_factory=lambda: _env_str(["SEMANTIC_AI_MODEL"], "moondream")
    )
    connect_timeout_seconds: float = 5.0
    inference_timeout_seconds: float = 60.0
    timeout_seconds: float = 60.0  # Backward compatibility
    fallback_stunt_score: float = 50.0
    fallback_humor_score: float = 55.0
    fallback_cinematic_score: float = 60.0
    weight_stunt: float = 0.40
    weight_humor: float = 0.35
    weight_cinematic: float = 0.25


@dataclass
class PipelineSettings:
    semantic_shortlist_size: int = 15
    auto_publish: bool = field(
        default_factory=lambda: _env_bool(["AUTO_PUBLISH"], False)
    )


@dataclass
class PublishingSettings:
    min_engagement_score: float = field(
        default_factory=lambda: _env_float(["AUTO_PUBLISH_MIN_SCORE"], 85.0)
    )
    auto_publish: bool = field(
        default_factory=lambda: _env_bool(["AUTO_PUBLISH"], False)
    )
    default_privacy: str = field(
        default_factory=lambda: _env_str(["YOUTUBE_DEFAULT_PRIVACY"], "private")
    )
    enforce_approval: bool = True
    enforce_in_simulation: bool = False
    strict_two_key_gate: bool = True


@dataclass
class RankingSettings:
    weight_motion: float = 0.35
    weight_audio: float = 0.15
    weight_semantic: float = 0.25
    weight_hook: float = 0.15
    weight_ending: float = 0.10


class Config:
    PROJECT_ROOT = PROJECT_ROOT
    INPUT_DIR = INPUT_DIR
    OUTPUT_DIR = OUTPUT_DIR
    CANDIDATES_DIR = CANDIDATES_DIR
    FINAL_DIR = FINAL_DIR
    BUFFER_DIR = BUFFER_DIR
    TEMPLATES_DIR = TEMPLATES_DIR
    ASSETS_DIR = ASSETS_DIR
    BGM_DIR = BGM_DIR
    SFX_DIR = SFX_DIR
    FONTS_DIR = FONTS_DIR
    DATABASE_PATH = DATABASE_PATH
    LOGS_DIR = LOGS_DIR

    FFMPEG_PATH = find_ffmpeg_binary()

    video = VideoSettings()
    audio = AudioSettings()
    language = LanguageVoiceSettings()
    youtube = YouTubeSettings()
    game = GameSettings()
    semantic = SemanticAnalysisSettings()
    pipeline = PipelineSettings()
    publishing = PublishingSettings()
    ranking = RankingSettings()
    stream = StreamSettings()
    resources = ResourceLimits()


config = Config()


