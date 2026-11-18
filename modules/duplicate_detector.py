"""
Duplicate Detector Module
Prevents duplicate clip generation, duplicate video ingestion, and duplicate YouTube uploads.
Uses cryptographic hashing and timestamp distance metrics.
"""

import hashlib
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from database.db import db

logger = logging.getLogger("gta6_agent.duplicate_detector")


class DuplicateDetector:
    def is_file_already_ingested(self, file_checksum: str) -> bool:
        """Check if identical raw video has already been ingested into the system."""
        existing = db.get_gameplay_by_checksum(file_checksum)
        return existing is not None

    def is_clip_duplicate(
        self, video_id: int, start_time: float, end_time: float, threshold_sec: float = 2.0
    ) -> bool:
        """
        Check if a clip with nearly identical start/end timestamps has already been extracted.
        """
        existing_clips = db.list_clips(limit=500)
        for c in existing_clips:
            if c["video_id"] == video_id:
                if (
                    abs(c["start_time"] - start_time) < threshold_sec
                    and abs(c["end_time"] - end_time) < threshold_sec
                ):
                    return True
        return False

    def is_already_uploaded(self, clip_id: int) -> bool:
        """
        Check if the clip has already been successfully uploaded to YouTube.
        """
        history = db.get_publishing_history()
        for record in history:
            if record["clip_id"] == clip_id and record["upload_status"] == "success":
                return True
        return False


duplicate_detector = DuplicateDetector()
