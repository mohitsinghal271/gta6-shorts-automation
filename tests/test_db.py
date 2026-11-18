"""
Unit Tests for Database Layer (SQLite)
"""

import os
import unittest
import tempfile
from pathlib import Path
from database.db import Database


class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_gta6.db"
        self.db = Database(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sources_crud(self):
        source_id = self.db.add_source(
            title="Rockstar Official Trailer 1",
            license_type="Rockstar Press Kit Official",
            creator_name="Rockstar Games",
            source_url="https://rockstargames.com/vi",
            permission_verified=True,
            notes="Official press b-roll",
        )
        self.assertGreater(source_id, 0)
        verified = self.db.get_verified_sources()
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0]["creator_name"], "Rockstar Games")

    def test_gameplay_ingestion(self):
        vid_id = self.db.insert_gameplay(
            filename="gta6_heist_test.mp4",
            filepath="/tmp/gta6_heist_test.mp4",
            file_size=1024000,
            duration=42.5,
            resolution_w=1920,
            resolution_h=1080,
            fps=30.0,
            checksum="abc123sha256hash",
        )
        self.assertGreater(vid_id, 0)

        record = self.db.get_gameplay_by_checksum("abc123sha256hash")
        self.assertIsNotNone(record)
        self.assertEqual(record["filename"], "gta6_heist_test.mp4")
        self.assertEqual(record["duration_seconds"], 42.5)

    def test_scenes_and_clips(self):
        vid_id = self.db.insert_gameplay(
            filename="test.mp4",
            filepath="/tmp/test.mp4",
            file_size=500000,
            duration=60.0,
            resolution_w=1920,
            resolution_h=1080,
            fps=30.0,
            checksum="hash456",
        )

        scenes = [
            {"start_time": 0.0, "end_time": 10.0, "duration": 10.0, "motion_score": 25.0, "scene_type": "chase"},
            {"start_time": 10.0, "end_time": 30.0, "duration": 20.0, "motion_score": 38.0, "scene_type": "high_action"},
        ]
        self.db.insert_scenes(vid_id, scenes)
        db_scenes = self.db.get_scenes(vid_id)
        self.assertEqual(len(db_scenes), 2)
        self.assertEqual(db_scenes[0]["scene_type"], "chase")

        clip_id = self.db.insert_clip(
            video_id=vid_id,
            start_time=5.0,
            end_time=35.0,
            duration=30.0,
            engagement_score=88.5,
            visual_score=85.0,
            action_score=90.0,
            scene_tags=["car_chase", "explosion"],
            language="hinglish",
            template_name="cinematic_hype",
            candidate_path="/tmp/cand1.mp4",
            status="pending_review",
        )
        self.assertGreater(clip_id, 0)

        clip = self.db.get_clip_by_id(clip_id)
        self.assertIsNotNone(clip)
        self.assertEqual(clip["engagement_score"], 88.5)
        self.assertIn("car_chase", clip["scene_tags"])

        # Update status
        self.db.update_clip_status(clip_id, "approved", final_path="/tmp/final1.mp4")
        clip = self.db.get_clip_by_id(clip_id)
        self.assertEqual(clip["status"], "approved")
        self.assertEqual(clip["final_path"], "/tmp/final1.mp4")

    def test_metadata_and_publishing(self):
        vid_id = self.db.insert_gameplay(
            filename="test.mp4",
            filepath="/tmp/test.mp4",
            file_size=100,
            duration=30.0,
            resolution_w=1920,
            resolution_h=1080,
            fps=30.0,
            checksum="h789",
        )
        clip_id = self.db.insert_clip(
            video_id=vid_id,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=92.0,
        )

        meta_id = self.db.insert_or_update_metadata(
            clip_id=clip_id,
            title_recommended="Insane GTA 6 Police Chase!",
            titles=["Title 1", "Title 2", "Title 3"],
            description="Epic chase scene.",
            hashtags=["#GTA6", "#Shorts"],
            tags=["GTA 6", "Gaming"],
            thumbnail_concept="Lucia smiling with neon background",
            pinned_comment="Drop your thoughts!",
        )
        self.assertGreater(meta_id, 0)
        meta = self.db.get_metadata(clip_id)
        self.assertEqual(meta["title_recommended"], "Insane GTA 6 Police Chase!")
        self.assertEqual(len(meta["titles"]), 3)

        # Record publishing
        pub_id = self.db.record_publishing(
            clip_id=clip_id,
            youtube_video_id="yt_12345",
            youtube_url="https://youtube.com/shorts/yt_12345",
            privacy_status="private",
            upload_status="success",
        )
        self.assertGreater(pub_id, 0)

        history = self.db.get_publishing_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["youtube_video_id"], "yt_12345")

        # KPI Stats check
        stats = self.db.get_dashboard_stats()
        self.assertEqual(stats["total_videos_processed"], 1)
        self.assertEqual(stats["total_clips_generated"], 1)
        self.assertEqual(stats["published_videos"], 1)


if __name__ == "__main__":
    unittest.main()
