"""
Scene Detector Module
Detects scene cuts, camera transitions, and visual shifts using frame sampling and pixel delta metrics.
Robust against missing packages: uses NumPy + FFmpeg frame pipe with optional OpenCV/PySceneDetect acceleration.
"""

import subprocess
import logging
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.scene_detector")


@dataclass
class SceneBoundary:
    scene_index: int
    start_time: float
    end_time: float
    duration: float
    motion_score: float = 0.0
    scene_cut_confidence: float = 0.0


class SceneDetector:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        self.sample_fps = 4.0
        self.min_scene_duration = 1.5
        self.cut_threshold = 28.0

    def detect_scenes_ffmpeg_numpy(
        self, video_path: Path, duration: float
    ) -> List[SceneBoundary]:
        w, h = 160, 90
        frame_bytes = w * h * 3

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={self.sample_fps},scale={w}:{h}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]

        # Use stderr=subprocess.DEVNULL to prevent pipe deadlocks
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        cut_timestamps = [0.0]
        prev_gray = None
        frame_idx = 0
        motion_scores = []
        recent_diffs = []

        try:
            while True:
                raw_frame = proc.stdout.read(frame_bytes)
                if not raw_frame or len(raw_frame) < frame_bytes:
                    break

                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((h, w, 3))
                gray = (
                    frame[:, :, 0] * 0.299 + frame[:, :, 1] * 0.587 + frame[:, :, 2] * 0.114
                ).astype(np.float32)

                timestamp = frame_idx / self.sample_fps

                if prev_gray is not None:
                    diff = np.mean(np.abs(gray - prev_gray))
                    recent_diffs.append(diff)

                    if (
                        diff > self.cut_threshold
                        and (timestamp - cut_timestamps[-1]) >= self.min_scene_duration
                    ):
                        cut_timestamps.append(timestamp)
                        motion_scores.append(np.mean(recent_diffs))
                        recent_diffs = []

                prev_gray = gray
                frame_idx += 1
        finally:
            if proc.stdout:
                proc.stdout.close()
            proc.wait()

        if not cut_timestamps or cut_timestamps[-1] < duration:
            cut_timestamps.append(duration)
            if recent_diffs:
                motion_scores.append(np.mean(recent_diffs))
            else:
                motion_scores.append(10.0)

        scenes = []
        for i in range(len(cut_timestamps) - 1):
            start = cut_timestamps[i]
            end = cut_timestamps[i + 1]
            dur = max(0.1, end - start)
            m_score = motion_scores[i] if i < len(motion_scores) else 15.0
            scenes.append(
                SceneBoundary(
                    scene_index=i,
                    start_time=round(start, 2),
                    end_time=round(end, 2),
                    duration=round(dur, 2),
                    motion_score=round(float(m_score), 2),
                    scene_cut_confidence=min(100.0, float(m_score) * 2.5),
                )
            )

        logger.info(f"Detected {len(scenes)} scenes in {video_path.name} (Duration: {duration:.1f}s)")
        return scenes

    def process_and_save_scenes(
        self, video_id: int, video_path: Path, duration: float
    ) -> List[Dict[str, Any]]:
        boundaries = self.detect_scenes_ffmpeg_numpy(video_path, duration)

        db_records = []
        for b in boundaries:
            if b.motion_score > 35.0:
                scene_type = "high_action"
            elif b.motion_score > 20.0:
                scene_type = "chase"
            elif b.motion_score > 12.0:
                scene_type = "action"
            else:
                scene_type = "cinematic"

            db_records.append(
                {
                    "start_time": b.start_time,
                    "end_time": b.end_time,
                    "duration": b.duration,
                    "motion_score": b.motion_score,
                    "audio_energy": 0.0,
                    "scene_type": scene_type,
                }
            )

        db.insert_scenes(video_id, db_records)
        return db_records


scene_detector = SceneDetector()
