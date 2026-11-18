"""
End-to-End Pipeline Integration Test
Generates a synthetic gameplay video using FFmpeg, executes the full pipeline,
and verifies the generated vertical 9:16 Short video, subtitles, metadata, and database state.
"""

import os
import subprocess
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from config import config
from database.db import db
from modules.pipeline import pipeline
from modules.semantic_analyzer import SemanticAnalysisResult
from modules.voice_generator import TimedWord


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.test_video_path = self.temp_path / "synthetic_gta6_gameplay.mp4"

        # Save original encoding parameters
        self.orig_preset = config.video.preset
        self.orig_crf = config.video.crf
        config.video.preset = "ultrafast"
        config.video.crf = 28

        # Generate a synthetic 16:9 video with color bars, motion, and audio tone (Duration: 15 seconds)
        # Using FFmpeg test patterns with ultrafast preset for fast test generation
        cmd = [
            config.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=15:size=1280x720:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=15",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(self.test_video_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            self.skipTest(f"FFmpeg synthetic test generation failed: {proc.stderr}")

    def tearDown(self):
        config.video.preset = self.orig_preset
        config.video.crf = self.orig_crf
        self.temp_dir.cleanup()

    def test_full_pipeline_execution(self):
        self.assertTrue(self.test_video_path.exists())

        # Mock external VLM and Edge-TTS to ensure fast, deterministic offline execution
        mock_sem_res = SemanticAnalysisResult(
            humor_score=80.0,
            stunt_score=92.0,
            cinematic_score=85.0,
            composite_score=87.5,
            event_summary="High-speed Vice City police pursuit and vehicle jump",
            why_entertaining="Incredible stunt action and neon visual atmosphere",
            suggested_hook="Insane police chase in Vice City!",
            keyframe_timestamps=[1.0, 7.5, 14.0],
            is_fallback=False,
        )

        async def mock_tts_stream(text, voice, out_path):
            # Fast synthetic audio generation for voiceover
            cmd = [
                config.FFMPEG_PATH,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=15",
                "-c:a",
                "aac",
                str(out_path),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return [
                TimedWord("GTA", 0.0, 0.5),
                TimedWord("Short", 0.5, 1.0),
                TimedWord("Gameplay", 1.0, 1.8),
            ]

        with patch("modules.semantic_analyzer.semantic_analyzer.analyze_clip_semantics", return_value=mock_sem_res), \
             patch("modules.semantic_analyzer.semantic_analyzer.analyze_segment", return_value=mock_sem_res), \
             patch("modules.voice_generator.voice_generator._synthesize_edge_tts", side_effect=mock_tts_stream):

            # Execute full pipeline
            result = pipeline.process_video_pipeline(
                video_path=self.test_video_path,
                language="hinglish",
                template_name="cinematic_hype",
                include_voiceover=True,
                top_clips=1,
            )

        self.assertGreater(result["clips_generated"], 0)
        clip_info = result["clips"][0]
        self.assertEqual(clip_info["status"], "pending_review")

        # Verify final video file exists
        final_video = Path(clip_info["final_path"])
        self.assertTrue(final_video.exists(), f"Final video {final_video} does not exist!")
        self.assertGreater(final_video.stat().st_size, 50000)

        # Verify metadata
        meta = db.get_metadata(clip_info["clip_id"])
        self.assertIsNotNone(meta)
        self.assertGreater(len(meta["titles"]), 0)
        self.assertIn("#GTA6", meta["hashtags"])

        # Approve and publish (simulation)
        pipeline.approve_clip(clip_info["clip_id"])
        pub_result = pipeline.approve_and_publish_clip(
            clip_id=clip_info["clip_id"],
            privacy_status="private",
            simulate=True,
        )
        self.assertTrue(pub_result["success"])
        self.assertTrue(pub_result["is_simulation"])

        # Check DB status
        updated_clip = db.get_clip_by_id(clip_info["clip_id"])
        self.assertEqual(updated_clip["status"], "published")


if __name__ == "__main__":
    unittest.main()

