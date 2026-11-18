"""
Clip Generator Module
Uses FFmpeg to extract sub-clips from raw gameplay footage with frame-accuracy,
maintaining audio-video synchronization and high visual quality.
"""

import os
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import config
from modules.video_analyzer import SegmentAnalysis
from database.db import db

logger = logging.getLogger("gta6_agent.clip_generator")


class ClipGenerator:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        self.output_dir = Path(config.CANDIDATES_DIR)

    def extract_clip(
        self,
        input_path: Path,
        start_time: float,
        duration: float,
        output_filename: Optional[str] = None,
    ) -> Path:
        """
        Extract sub-clip using FFmpeg with fast seeking and high quality re-encoding.
        Guarantees clean I-frame start and perfectly synchronized audio.
        """
        input_path = Path(input_path).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        if not output_filename:
            base = input_path.stem
            output_filename = f"clip_{base}_{int(start_time)}_{int(start_time + duration)}.mp4"

        output_path = self.output_dir / output_filename
        os.makedirs(self.output_dir, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-ss",
            f"{start_time:.3f}",
            "-i",
            str(input_path),
            "-t",
            f"{duration:.3f}",
            "-c:v",
            config.video.video_codec,
            "-preset",
            config.video.preset,
            "-crf",
            str(config.video.crf),
            "-c:a",
            config.video.audio_codec,
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            str(config.resources.ffmpeg_cpu_threads),
            "-avoid_negative_ts",
            "make_zero",
            str(output_path),
        ]

        logger.info(f"Extracting sub-clip: {start_time:.2f}s to {start_time + duration:.2f}s -> {output_path.name}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if proc.returncode != 0:
            logger.error(f"FFmpeg clip extraction failed: {proc.stderr}")
            raise RuntimeError(f"FFmpeg error during clipping: {proc.stderr}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Output clip was not created or empty: {output_path}")

        return output_path

    def generate_candidate_clips(
        self,
        video_id: int,
        input_path: Path,
        ranked_segments: List[SegmentAnalysis],
        language: str = "hinglish",
        template_name: str = "cinematic_hype",
    ) -> List[Dict[str, Any]]:
        """
        Extract files for all top ranked segments and register them into the database.
        """
        generated = []
        for idx, seg in enumerate(ranked_segments):
            try:
                candidate_filename = f"vid_{video_id}_clip_{idx + 1}_{int(seg.start_time)}s.mp4"
                clip_path = self.extract_clip(
                    input_path=input_path,
                    start_time=seg.start_time,
                    duration=seg.duration,
                    output_filename=candidate_filename,
                )

                is_fallback_raw = getattr(seg, "is_fallback", None)
                if is_fallback_raw is None:
                    is_fallback_raw = getattr(seg, "semantic_is_fallback", None)
                is_fallback = bool(is_fallback_raw) if is_fallback_raw is not None else False

                status_raw = getattr(seg, "semantic_status", None)
                if status_raw:
                    semantic_status = status_raw
                else:
                    semantic_status = "FALLBACK" if is_fallback else ("SUCCESS" if getattr(seg, "semantic_score", 0.0) > 0.0 else "PENDING")

                clip_id = db.insert_clip(
                    video_id=video_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    duration=seg.duration,
                    engagement_score=seg.composite_score,
                    visual_score=seg.visual_excitement,
                    action_score=seg.action_intensity,
                    audio_score=seg.audio_intensity,
                    unpredictability_score=seg.unpredictability,
                    hook_score=seg.hook_potential,
                    ending_score=seg.ending_quality,
                    scene_tags=seg.tags,
                    language=language,
                    template_name=template_name,
                    semantic_score=getattr(seg, "semantic_score", 0.0) or 0.0,
                    humor_score=getattr(seg, "humor_score", 0.0) or 0.0,
                    stunt_score=getattr(seg, "stunt_score", 0.0) or 0.0,
                    cinematic_score=getattr(seg, "cinematic_score", 0.0) or 0.0,
                    event_summary=getattr(seg, "event_summary", None),
                    is_fallback=1 if is_fallback else 0,
                    semantic_status=semantic_status,
                    candidate_path=str(clip_path),
                    status="pending_review",
                )

                generated.append(
                    {
                        "clip_id": clip_id,
                        "candidate_path": str(clip_path),
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "duration": seg.duration,
                        "engagement_score": seg.composite_score,
                        "tags": seg.tags,
                        "semantic_info": {
                            "semantic_score": getattr(seg, "semantic_score", 0.0) or 0.0,
                            "humor_score": getattr(seg, "humor_score", 0.0) or 0.0,
                            "stunt_score": getattr(seg, "stunt_score", 0.0) or 0.0,
                            "cinematic_score": getattr(seg, "cinematic_score", 0.0) or 0.0,
                            "event_summary": getattr(seg, "event_summary", None),
                            "why_entertaining": getattr(seg, "why_entertaining", None),
                            "suggested_hook": getattr(seg, "suggested_hook", None),
                            "keyframe_timestamps": getattr(seg, "keyframe_timestamps", None),
                            "is_fallback": is_fallback,
                            "semantic_status": semantic_status,
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error generating clip for segment {seg.start_time}-{seg.end_time}: {e}")


        logger.info(f"Generated {len(generated)} candidate clips for video {video_id}")
        return generated


clip_generator = ClipGenerator()
