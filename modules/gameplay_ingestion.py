"""
Gameplay Ingestion Module
Handles video ingestion from local folders, user uploads, and watched directories.
Extracts container information, technical metadata, and validates video integrity.
"""

import os
import re
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.ingestion")


@dataclass
class VideoMetadata:
    filepath: str
    filename: str
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    fps: float
    bitrate: Optional[int]
    has_audio: bool
    checksum_sha256: str


class GameplayIngestionService:
    def __init__(self, input_dir: Optional[Path] = None, ffmpeg_path: Optional[str] = None):
        self.input_dir = Path(input_dir or config.INPUT_DIR)
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        self.supported_exts = set(config.video.supported_extensions)

    def compute_sha256(self, filepath: Path, chunk_size: int = 65536) -> str:
        """Compute SHA256 hash of a video file for deduplication."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def probe_video(self, filepath: Path) -> VideoMetadata:
        """
        Probe video properties using FFmpeg.
        Parses video duration, resolution, fps, bitrate, and audio streams.
        """
        cmd = [self.ffmpeg_path, "-hide_banner", "-i", str(filepath)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stderr

        # Duration parsing
        duration = 0.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
        if dur_match:
            h, m, s = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)

        # Bitrate parsing
        bitrate = None
        bit_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", output)
        if bit_match:
            bitrate = int(bit_match.group(1)) * 1000

        # Video stream parsing: resolution and FPS
        width, height = 1920, 1080
        fps = 30.0
        res_match = re.search(r"Video:.*?,\s*(\d{3,5})x(\d{3,5})", output)
        if res_match:
            width = int(res_match.group(1))
            height = int(res_match.group(2))

        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", output)
        if fps_match:
            fps = float(fps_match.group(1))

        # Check for audio stream
        has_audio = bool(re.search(r"Audio:\s*", output))

        file_size = filepath.stat().st_size
        checksum = self.compute_sha256(filepath)

        return VideoMetadata(
            filepath=str(filepath),
            filename=filepath.name,
            file_size_bytes=file_size,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            bitrate=bitrate,
            has_audio=has_audio,
            checksum_sha256=checksum,
        )

    def ingest_video_file(
        self, filepath: Path, source_id: Optional[int] = None, force_reprocess: bool = False
    ) -> Tuple[int, VideoMetadata]:
        """
        Ingest a single video file into the system:
        - Check for duplicate via SHA256
        - Probe video metadata
        - Save record to SQLite
        """
        filepath = Path(filepath).resolve()
        if not filepath.exists():
            raise FileNotFoundError(f"Video file not found at {filepath}")

        if filepath.suffix.lower() not in self.supported_exts:
            raise ValueError(
                f"Unsupported video format: {filepath.suffix}. Supported: {self.supported_exts}"
            )

        metadata = self.probe_video(filepath)
        min_req_duration = config.video.min_clip_duration
        if metadata.duration_seconds < min_req_duration:
            raise ValueError(
                f"Video too short ({metadata.duration_seconds:.1f}s). "
                f"Minimum required duration for YouTube Shorts is {min_req_duration:.0f} seconds."
            )

        # Check if already ingested
        existing = db.get_gameplay_by_checksum(metadata.checksum_sha256)
        if existing and not force_reprocess:
            logger.info(f"Video {filepath.name} already ingested with ID: {existing['id']}")
            return existing["id"], metadata

        video_id = db.insert_gameplay(
            filename=metadata.filename,
            filepath=metadata.filepath,
            file_size=metadata.file_size_bytes,
            duration=metadata.duration_seconds,
            resolution_w=metadata.width,
            resolution_h=metadata.height,
            fps=metadata.fps,
            checksum=metadata.checksum_sha256,
            source_id=source_id,
        )
        logger.info(
            f"Successfully ingested {metadata.filename} [ID: {video_id}, Duration: {metadata.duration_seconds:.1f}s, Res: {metadata.width}x{metadata.height}]"
        )
        return video_id, metadata

    def scan_and_ingest_input_folder(self) -> List[Tuple[int, VideoMetadata]]:
        """
        Scan watched input directory for all video files and ingest any new ones.
        """
        results = []
        if not self.input_dir.exists():
            return results

        for entry in self.input_dir.iterdir():
            if entry.is_file() and entry.suffix.lower() in self.supported_exts:
                try:
                    vid_id, meta = self.ingest_video_file(entry)
                    results.append((vid_id, meta))
                except Exception as e:
                    logger.error(f"Failed to ingest {entry.name}: {e}")
        return results


ingestion_service = GameplayIngestionService()
