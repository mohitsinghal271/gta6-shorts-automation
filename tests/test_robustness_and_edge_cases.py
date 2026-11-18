"""
Unit Tests for Robustness, Edge Cases, and Bug Regressions
Tests:
- Handling gameplay videos without audio streams
- Handling non-standard video aspect ratios (odd dimensions preventing libx264 divisible-by-2 crashes)
- Socket context management in is_internet_available
- Duration validation (minimum 15s Shorts constraint)
- Editing template rendering (dynamic zoom and vignette)
"""

import os
import subprocess
import unittest
import tempfile
import warnings
from pathlib import Path

from config import config
from modules.audio_processor import audio_processor
from modules.video_editor import video_editor
from modules.voice_generator import VoiceoverResult, is_internet_available
from modules.gameplay_ingestion import GameplayIngestionService


class TestRobustnessAndEdgeCases(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # 1. Generate video without audio track (5 seconds, 640x360)
        self.no_audio_video = self.temp_path / "video_no_audio.mp4"
        cmd1 = [
            config.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=5:size=640x360:rate=30",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(self.no_audio_video),
        ]
        subprocess.run(cmd1, check=True)

        # 2. Generate video with odd aspect ratio (1001x555 in AVI using mjpeg to test aspect scaling)
        self.odd_res_video = self.temp_path / "video_odd_res.avi"
        cmd2 = [
            config.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=3:size=1001x555:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=3",
            "-c:v",
            "mjpeg",
            "-c:a",
            "pcm_s16le",
            str(self.odd_res_video),
        ]
        subprocess.run(cmd2, check=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_audio_presence_detection(self):
        self.assertFalse(audio_processor.has_audio_stream(self.no_audio_video))
        self.assertTrue(audio_processor.has_audio_stream(self.odd_res_video))

    def test_mix_audio_on_video_without_audio(self):
        out_audio = self.temp_path / "mixed_silence.aac"
        audio_processor.mix_audio_tracks(
            gameplay_video=self.no_audio_video,
            voiceover_audio=None,
            output_audio_path=out_audio,
            duration=3.0,
            include_voiceover=False,
        )
        self.assertTrue(out_audio.exists())
        self.assertGreater(out_audio.stat().st_size, 1000, "Audio track must not be 0 bytes")

    def test_render_short_from_no_audio_video(self):
        vr = VoiceoverResult(
            audio_path=None,
            script_text="Testing no audio",
            language="english",
            voice_name="test",
            duration=0.0,
            timed_words=[],
            is_silent=True,
        )
        final_video = video_editor.render_final_short(
            clip_id=888,
            candidate_clip_path=self.no_audio_video,
            duration=3.0,
            voiceover_result=vr,
            template_name="cinematic_hype",
        )
        self.assertTrue(final_video.exists())
        self.assertGreater(final_video.stat().st_size, 10000)

    def test_render_odd_resolution_video_no_libx264_crash(self):
        vr = VoiceoverResult(
            audio_path=None,
            script_text="",
            language="hinglish",
            voice_name="test",
            duration=0.0,
            timed_words=[],
            is_silent=True,
        )
        # Tests both blurred_background_stack (scale=1080:-2) and action_fast (intelligent_center_crop)
        final_video_blur = video_editor.render_final_short(
            clip_id=889,
            candidate_clip_path=self.odd_res_video,
            duration=2.0,
            voiceover_result=vr,
            template_name="cinematic_hype",
        )
        self.assertTrue(final_video_blur.exists())

        final_video_action = video_editor.render_final_short(
            clip_id=890,
            candidate_clip_path=self.odd_res_video,
            duration=2.0,
            voiceover_result=vr,
            template_name="action_fast",
        )
        self.assertTrue(final_video_action.exists())

    def test_is_internet_available_socket_closure_no_resource_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", ResourceWarning)
            # Port 1 is typically closed/unreachable, triggering the exception path
            status = is_internet_available(host="127.0.0.1", port=1, timeout=0.1)
            self.assertFalse(status)
            resource_warnings = [item for item in w if issubclass(item.category, ResourceWarning)]
            self.assertEqual(len(resource_warnings), 0, "Socket must be closed with no ResourceWarning")

    def test_ingestion_rejects_sub_15s_videos(self):
        ingestion = GameplayIngestionService(input_dir=self.temp_path)
        with self.assertRaises(ValueError) as ctx:
            ingestion.ingest_video_file(self.no_audio_video)  # duration is 5s < 15s
        self.assertIn("Minimum required duration for YouTube Shorts is 15 seconds", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
