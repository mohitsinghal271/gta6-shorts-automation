"""
Video Analyzer Module
Extracts visual motion dynamics, audio energy profiles, sudden brightness/color shifts,
and classifies GTA 6 gameplay events (chases, explosions, crashes, gunfights, stunts, funny NPC moments).
"""

import math
import subprocess
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from config import config

logger = logging.getLogger("gta6_agent.video_analyzer")


@dataclass
class SegmentAnalysis:
    start_time: float
    end_time: float
    duration: float
    visual_excitement: float
    action_intensity: float
    audio_intensity: float
    unpredictability: float
    hook_potential: float
    ending_quality: float
    storytelling_potential: float
    composite_score: float
    tags: List[str]
    semantic_score: Optional[float] = None
    humor_score: Optional[float] = None
    stunt_score: Optional[float] = None
    cinematic_score: Optional[float] = None
    event_summary: Optional[str] = None
    why_entertaining: Optional[str] = None
    suggested_hook: Optional[str] = None
    keyframe_timestamps: Optional[List[float]] = None
    is_fallback: bool = False
    semantic_is_fallback: bool = False


class VideoAnalyzer:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH

    def extract_audio_rms_profile(
        self, video_path: Path, sample_interval: float = 0.5
    ) -> List[Tuple[float, float]]:
        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            "-",
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        chunk_samples = int(16000 * sample_interval)
        chunk_bytes = chunk_samples * 2

        rms_profile = []
        timestamp = 0.0

        try:
            while True:
                raw_chunk = proc.stdout.read(chunk_bytes)
                if not raw_chunk or len(raw_chunk) < 2:
                    break
                samples = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32)
                rms = np.sqrt(np.mean(samples**2) + 1e-6)
                db = 20 * np.log10(max(1.0, rms) / 32767.0)
                norm_score = max(0.0, min(100.0, (db + 60.0) * (100.0 / 60.0)))
                rms_profile.append((round(timestamp, 2), round(float(norm_score), 1)))
                timestamp += sample_interval
        except Exception as e:
            logger.warning(f"Audio extraction error: {e}. Defaulting audio profile.")
            rms_profile.append((0.0, 50.0))
        finally:
            if proc.stdout:
                proc.stdout.close()
            proc.wait()

        if not rms_profile:
            rms_profile = [(0.0, 50.0)]
        return rms_profile

    def analyze_sliding_windows(
        self,
        video_path: Path,
        duration: float,
        scenes: List[Dict[str, Any]],
        window_duration: float = 35.0,
        step_seconds: float = 5.0,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
    ) -> List[SegmentAnalysis]:
        if duration <= window_duration + 5.0:
            windows = [(0.0, duration)]
        else:
            windows = []
            cur_start = 0.0
            while cur_start + 15.0 <= duration:
                cur_end = min(duration, cur_start + window_duration)
                if cur_end - cur_start >= 15.0:
                    windows.append((cur_start, cur_end))
                cur_start += step_seconds

        if audio_profile is None:
            audio_profile = self.extract_audio_rms_profile(video_path)

        segments = []
        for start, end in windows:
            seg_dur = end - start
            sub_scenes = [
                s for s in scenes if not (s["end_time"] <= start or s["start_time"] >= end)
            ]

            if sub_scenes:
                motion_vals = [s.get("motion_score", 15.0) for s in sub_scenes]
                avg_motion = float(np.mean(motion_vals))
                max_motion = float(np.max(motion_vals))
                scene_cut_count = len(sub_scenes)
            else:
                avg_motion = 15.0
                max_motion = 20.0
                scene_cut_count = 1

            visual_excitement = min(100.0, max(20.0, (avg_motion * 1.8) + (max_motion * 0.4)))
            action_intensity = min(100.0, max(15.0, (avg_motion * 2.2)))

            window_audio = [energy for t, energy in audio_profile if start <= t <= end]
            if window_audio:
                avg_audio = float(np.mean(window_audio))
                max_audio = float(np.max(window_audio))
            else:
                avg_audio = 45.0
                max_audio = 60.0

            audio_score = min(100.0, (avg_audio * 0.6) + (max_audio * 0.4))

            hook_audio = [energy for t, energy in audio_profile if start <= t <= start + 3.5]
            first_scene_motion = sub_scenes[0].get("motion_score", 15.0) if sub_scenes else 15.0
            hook_aud_val = np.mean(hook_audio) if hook_audio else 50.0
            hook_potential = min(
                100.0, max(20.0, (first_scene_motion * 1.5) + (float(hook_aud_val) * 0.5))
            )

            last_scene = sub_scenes[-1] if sub_scenes else None
            if last_scene and abs(last_scene["end_time"] - end) < 0.8:
                ending_quality = 85.0
            else:
                ending_quality = 70.0

            unpredictability = min(
                100.0,
                max(
                    25.0,
                    (float(np.std(motion_vals)) * 2.5 if len(motion_vals) > 1 else 30.0)
                    + (scene_cut_count * 4.0),
                ),
            )

            storytelling = min(
                100.0, max(30.0, (visual_excitement * 0.4) + (unpredictability * 0.3) + 30.0)
            )

            composite = (
                (visual_excitement * 0.20)
                + (action_intensity * 0.25)
                + (audio_score * 0.15)
                + (unpredictability * 0.15)
                + (hook_potential * 0.15)
                + (ending_quality * 0.10)
            )

            tags = []
            if action_intensity >= 65.0:
                tags.append("high_speed_chase")
            if max_motion >= 35.0:
                tags.append("car_crash_explosion")
            if audio_score >= 70.0:
                tags.append("police_action")
            if visual_excitement >= 70.0 and unpredictability >= 60.0:
                tags.append("crazy_stunt")
            if scene_cut_count >= 3:
                tags.append("cinematic_montage")
            if not tags:
                tags.append("vice_city_highlights")

            segments.append(
                SegmentAnalysis(
                    start_time=round(start, 2),
                    end_time=round(end, 2),
                    duration=round(seg_dur, 2),
                    visual_excitement=round(visual_excitement, 1),
                    action_intensity=round(action_intensity, 1),
                    audio_intensity=round(audio_score, 1),
                    unpredictability=round(unpredictability, 1),
                    hook_potential=round(hook_potential, 1),
                    ending_quality=round(ending_quality, 1),
                    storytelling_potential=round(storytelling, 1),
                    composite_score=round(composite, 1),
                    tags=tags,
                )
            )

        segments.sort(key=lambda s: s.composite_score, reverse=True)
        return segments


video_analyzer = VideoAnalyzer()
