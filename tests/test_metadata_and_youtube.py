"""
Unit Tests for Metadata Generator, Duplicate Detector, and YouTube Automation
"""

import sys
import uuid
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from database.db import Database, db
from modules.metadata_generator import MetadataGenerator
from modules.duplicate_detector import DuplicateDetector
from modules.youtube_uploader import YouTubeUploader


class TestMetadataAndYouTube(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.meta_gen = MetadataGenerator()
        self.dup_detector = DuplicateDetector()
        self.uploader = YouTubeUploader()

        # Insert unique video & clip record per test
        uid = uuid.uuid4().hex[:8]
        self.video_id = db.insert_gameplay(
            filename=f"test_gta6_{uid}.mp4",
            filepath=str(self.temp_path / f"test_gta6_{uid}.mp4"),
            file_size=1000,
            duration=30.0,
            resolution_w=1920,
            resolution_h=1080,
            fps=30.0,
            checksum=f"test_checksum_{uid}",
        )
        self.clip_id = db.insert_clip(
            video_id=self.video_id,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=95.0,
        )
        db.set_clip_approval(self.clip_id, approved=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_generation_and_disclaimer(self):
        meta = self.meta_gen.generate_metadata(
            clip_id=self.clip_id,
            language="hinglish",
            tags=["car_crash_explosion"],
        )
        self.assertEqual(len(meta.titles), 3)
        self.assertTrue(len(meta.title_recommended) > 0)
        self.assertIn("#GTA6", meta.hashtags)
        self.assertIn("Rockstar Games", meta.disclaimer)
        self.assertIn("Fair Use", meta.disclaimer)
        self.assertTrue(len(meta.pinned_comment) > 0)

    def test_youtube_uploader_simulation(self):
        dummy_vid = self.temp_path / "test_short.mp4"
        dummy_vid.write_bytes(b"dummy_mp4_content")

        res = self.uploader.upload_short(
            clip_id=self.clip_id,
            video_path=dummy_vid,
            title="GTA 6 Epic Stunt",
            description="Testing YouTube upload",
            tags=["GTA 6", "Shorts"],
            privacy_status="private",
            simulate=True,
        )
        self.assertTrue(res.success)
        self.assertTrue(res.is_simulation)
        self.assertIn(f"sim_{self.clip_id}", res.youtube_video_id)
        self.assertIn("https://youtube.com/shorts/", res.youtube_url)

        # Check duplicate upload prevention
        dup_res = self.uploader.upload_short(
            clip_id=self.clip_id,
            video_path=dummy_vid,
            title="GTA 6 Epic Stunt Duplicate",
            description="Should be rejected",
            tags=["GTA 6"],
            simulate=True,
        )
        self.assertFalse(dup_res.success)
        self.assertIn("already been uploaded", dup_res.error_message)


if __name__ == "__main__":
    unittest.main()
