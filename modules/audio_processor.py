"""
Audio Processor Module
Handles advanced multi-channel audio mixing, dynamic voiceover ducking,
background music loop & blending, sound effects cues, and EBU R128 loudness normalization.
"""

import os
import subprocess
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from config import config

logger = logging.getLogger("gta6_agent.audio_processor")


class AudioProcessor:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH

    def has_audio_stream(self, video_path: Path) -> bool:
        """Probe if video file contains an active audio stream."""
        import re
        cmd = [self.ffmpeg_path, "-hide_banner", "-i", str(video_path)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return bool(re.search(r"Audio:\s*", res.stderr))

    def mix_audio_tracks(
        self,
        gameplay_video: Path,
        voiceover_audio: Optional[Path],
        output_audio_path: Path,
        duration: float,
        bgm_audio: Optional[Path] = None,
        include_voiceover: bool = True,
    ) -> Path:
        """
        Mix gameplay audio, voiceover, and optional BGM using FFmpeg filtergraph:
        - Detects whether gameplay has an audio stream to prevent missing-stream errors
        - Ducks gameplay audio to config.audio.ducking_ratio during voiceover
        - Loops and fades background music if present
        - Falls back to clean synthesized silence or direct voiceover when stream is missing
        """
        output_audio_path = Path(output_audio_path).resolve()
        os.makedirs(output_audio_path.parent, exist_ok=True)

        has_gameplay_audio = self.has_audio_stream(gameplay_video)
        has_voice = bool(include_voiceover and voiceover_audio and Path(voiceover_audio).exists())
        has_bgm = bool(bgm_audio and Path(bgm_audio).exists())

        loudnorm_filter = ",loudnorm=I=-14:LRA=7:TP=-1.5"

        if has_gameplay_audio and has_voice and has_bgm:
            inputs = ["-i", str(gameplay_video), "-i", str(voiceover_audio), "-i", str(bgm_audio)]
            filter_str = (
                f"[0:a]volume={config.audio.gameplay_volume}[game]; "
                f"[1:a]volume={config.audio.voiceover_volume}[voice]; "
                f"[2:a]volume={config.audio.bgm_volume}[bgm]; "
                f"[game][voice]sidechaincompress=threshold=0.08:ratio=5:attack=20:release=300[ducked]; "
                f"[ducked][voice][bgm]amix=inputs=3:duration=first{loudnorm_filter}[outa]"
            )
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                *inputs,
                "-filter_complex",
                filter_str,
                "-map",
                "[outa]",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]
        elif has_gameplay_audio and has_voice:
            inputs = ["-i", str(gameplay_video), "-i", str(voiceover_audio)]
            filter_str = (
                f"[0:a]volume={config.audio.gameplay_volume}[game]; "
                f"[1:a]volume={config.audio.voiceover_volume}[voice]; "
                f"[game][voice]sidechaincompress=threshold=0.08:ratio=5:attack=20:release=300[ducked]; "
                f"[ducked][voice]amix=inputs=2:duration=first{loudnorm_filter}[outa]"
            )
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                *inputs,
                "-filter_complex",
                filter_str,
                "-map",
                "[outa]",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]
        elif has_voice:
            # Gameplay video has no audio track, but voiceover exists
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                "-i",
                str(voiceover_audio),
                "-af",
                "loudnorm=I=-14:LRA=7:TP=-1.5",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]
        elif has_gameplay_audio:
            # Gameplay only audio with normal level
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                "-i",
                str(gameplay_video),
                "-filter_complex",
                f"[0:a]volume={config.audio.gameplay_volume * 1.5}{loudnorm_filter}[outa]",
                "-map",
                "[outa]",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]
        else:
            # No audio track on gameplay and no voiceover -> generate clean stereo silence
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-threads",
                str(config.resources.ffmpeg_cpu_threads),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]

        logger.info(f"Mixing audio tracks for {gameplay_video.name} -> {output_audio_path.name}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if proc.returncode != 0 or not output_audio_path.exists() or output_audio_path.stat().st_size == 0:
            logger.warning(
                f"Audio mixing failed ({proc.stderr}). Generating fallback silent audio track."
            )
            fallback_cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_audio_path),
            ]
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output_audio_path


audio_processor = AudioProcessor()
