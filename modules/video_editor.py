"""
Video Editor Module
Performs vertical 9:16 1080x1920 transformation, intelligent cropping, blurred background stacking,
cinematic color grading, subtitle burning, and template-based professional gaming edits via FFmpeg.
"""

import os
import subprocess
import logging
import json
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from config import config
from modules.voice_generator import VoiceoverResult
from modules.subtitle_generator import subtitle_generator
from modules.audio_processor import audio_processor

logger = logging.getLogger("gta6_agent.video_editor")


def probe_source_fps(video_path: Path) -> float:
    """Probes exact container and stream framerate using ffprobe."""
    ffprobe_bin = config.FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe") if "ffmpeg.exe" in config.FFMPEG_PATH else "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,avg_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        r_fps = stream.get("r_frame_rate") or stream.get("avg_frame_rate") or "30/1"
        num, den = map(float, r_fps.split("/"))
        return num / den if den != 0 else 30.0
    except Exception as e:
        logger.warning("Could not probe FPS for %s (%s); defaulting to 30.0 FPS", video_path, e)
        return 30.0


def determine_target_fps(source_fps: float) -> int:
    """Calculates conditional target FPS without artificial frame duplication."""
    if source_fps >= 59.0:
        return 60
    elif source_fps >= 29.0:
        return 30
    else:
        return int(round(source_fps))

# Editing templates definitions
EDITING_TEMPLATES = {
    "cinematic_hype": {
        "crop_mode": "blurred_background_stack",
        "color_eq": "eq=contrast=1.08:saturation=1.18:brightness=0.02",
        "zoom_effect": False,
        "vignette": True,
        "description": "Blurred background stack with vibrant Vice City neon aesthetic and high-contrast color grading.",
    },
    "action_fast": {
        "crop_mode": "intelligent_center_crop",
        "color_eq": "eq=contrast=1.12:saturation=1.20:brightness=0.01",
        "zoom_effect": True,
        "vignette": False,
        "description": "Full vertical center-crop with subtle dynamic action zoom and punchy saturation.",
    },
    "story_npc": {
        "crop_mode": "blurred_background_stack",
        "color_eq": "eq=contrast=1.04:saturation=1.08:brightness=0.0",
        "zoom_effect": False,
        "vignette": False,
        "description": "Natural cinematic grading focused on clear dialogue and NPC interactions.",
    },
    "funny_moments": {
        "crop_mode": "blurred_background_stack",
        "color_eq": "eq=contrast=1.10:saturation=1.25:brightness=0.03",
        "zoom_effect": False,
        "vignette": False,
        "description": "Vibrant comedy styling with fast visual cuts and colorful framing.",
    },
}


class VideoEditor:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        self.output_dir = Path(config.FINAL_DIR)
        os.makedirs(self.output_dir, exist_ok=True)

    def _build_filtergraph(
        self,
        template_name: str,
        duration: float,
        ass_subtitle_path: Optional[Path] = None,
        target_fps: int = 30,
    ) -> str:
        """
        Build professional 9:16 vertical 1080x1920 filtergraph for FFmpeg:
        Mode 1 (blurred_background_stack):
        - Background: scale to 1080x1920 crop, heavy blur (boxblur=25:5) + darken (eq=brightness=-0.15)
        - Foreground: scale to 1080 width preserving 16:9 aspect (1080x608), centered at y=(1920-608)/2 = 656
        - Apply template color grading
        - Overlay subtitles
        """
        template = EDITING_TEMPLATES.get(template_name, EDITING_TEMPLATES["cinematic_hype"])
        crop_mode = template.get("crop_mode", "blurred_background_stack")
        color_eq = template.get("color_eq", "eq=contrast=1.08:saturation=1.15")

        filters = []
        vignette_str = ",vignette=PI/5" if (template.get("vignette") and config.video.preset != "ultrafast") else ""

        if crop_mode == "blurred_background_stack":
            # Split stream into background [bg] and foreground [fg]
            # Efficiently blur at reduced resolution then upscale, yielding identical visual blur at 4-5x speed
            bg_chain = (
                "[0:v]scale=270:480:force_original_aspect_ratio=increase,"
                "crop=270:480,"
                "boxblur=12:2,"
                "scale=1080:1920,"
                "eq=brightness=-0.18[bg];"
            )
            fg_chain = (
                "[0:v]scale=1080:-2[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
                f"[merged]{color_eq}{vignette_str}[graded]"
            )
            filters.append(bg_chain + fg_chain)
            last_tag = "[graded]"

        else:
            # Intelligent center crop: scale ensuring dimensions >= 1080x1920 before cropping
            zoom_str = (
                f",zoompan=z='min(zoom+0.0005,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={target_fps}"
                if template.get("zoom_effect")
                else ""
            )
            center_chain = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920"
                f"{zoom_str},"
                f"{color_eq}{vignette_str}[graded]"
            )
            filters.append(center_chain)
            last_tag = "[graded]"

        # Subtitle burning via ASS filter if subtitles exist
        if ass_subtitle_path and Path(ass_subtitle_path).exists():
            # In Windows, escape backslashes, colons, and single quotes for ffmpeg filter: C\:/path/to/sub.ass
            sub_escaped = (
                str(ass_subtitle_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
            )
            filters.append(f"{last_tag}subtitles='{sub_escaped}'[vfinal]")
            last_tag = "[vfinal]"

        return ";".join(filters)

    def render_final_short(
        self,
        clip_id: int,
        candidate_clip_path: Path,
        duration: float,
        voiceover_result: VoiceoverResult,
        template_name: str = "cinematic_hype",
    ) -> Path:
        """
        Renders the complete, polished YouTube Short:
        1. Mixes audio (gameplay + voiceover ducking)
        2. Generates animated ASS karaoke subtitles
        3. Transforms video to vertical 9:16 (1080x1920)
        4. Encodes using H.264 high profile with YouTube recommended settings.
        """
        candidate_clip_path = Path(candidate_clip_path).resolve()
        final_filename = f"short_{clip_id}_{template_name}_{voiceover_result.language}.mp4"
        final_path = self.output_dir / final_filename

        # Probe source FPS and calculate conditional target FPS
        source_fps = probe_source_fps(candidate_clip_path)
        target_fps = determine_target_fps(source_fps)

        # 1. Generate Subtitles if voiceover words exist
        ass_sub_path = None
        if voiceover_result.timed_words:
            ass_sub_path = subtitle_generator.generate_ass_karaoke(
                timed_words=voiceover_result.timed_words,
                clip_id=clip_id,
                words_per_group=3,
            )

        # 2. Mix Audio
        temp_audio = config.OUTPUT_DIR / f"temp_mix_{clip_id}.aac"
        audio_processor.mix_audio_tracks(
            gameplay_video=candidate_clip_path,
            voiceover_audio=voiceover_result.audio_path,
            output_audio_path=temp_audio,
            duration=duration,
            include_voiceover=not voiceover_result.is_silent,
        )

        # 3. Build Video Filter
        filtergraph = self._build_filtergraph(
            template_name=template_name,
            duration=duration,
            ass_subtitle_path=ass_sub_path,
            target_fps=target_fps,
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            str(candidate_clip_path),
            "-i",
            str(temp_audio),
            "-filter_complex",
            filtergraph,
            "-map",
            "[vfinal]" if "[vfinal]" in filtergraph else "[graded]",
            "-map",
            "1:a",
            "-t",
            f"{duration:.3f}",
            "-r",
            str(target_fps),
            "-c:v",
            config.video.video_codec,
            "-preset",
            config.video.preset,
            "-crf",
            str(config.video.crf),
            "-b:v",
            config.video.video_bitrate,
            "-c:a",
            config.video.audio_codec,
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            str(config.resources.ffmpeg_cpu_threads),
            "-movflags",
            "+faststart",
            str(final_path),
        ]

        logger.info(f"Rendering final short {final_path.name} with template '{template_name}' at {target_fps} FPS...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if proc.returncode != 0:
            logger.warning(
                f"Full filtergraph render error: {proc.stderr}. Attempting fallback render without subtitles."
            )
            # Fallback without subtitles in case fontconfig / subtitle library had an issue
            fallback_filter = self._build_filtergraph(
                template_name=template_name, duration=duration, ass_subtitle_path=None, target_fps=target_fps
            )
            fallback_cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-i",
                str(candidate_clip_path),
                "-i",
                str(temp_audio),
                "-filter_complex",
                fallback_filter,
                "-map",
                "[graded]",
                "-map",
                "1:a",
                "-t",
                f"{duration:.3f}",
                "-r",
                str(target_fps),
                "-c:v",
                config.video.video_codec,
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                "-pix_fmt",
                "yuv420p",
                str(final_path),
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Cleanup temp audio
        if temp_audio.exists():
            try:
                temp_audio.unlink()
            except Exception:
                pass

        if not final_path.exists() or final_path.stat().st_size == 0:
            raise RuntimeError(f"Failed to produce final short at {final_path}")

        logger.info(f"Final YouTube Short created: {final_path} (Size: {final_path.stat().st_size} bytes)")
        return final_path


video_editor = VideoEditor()
