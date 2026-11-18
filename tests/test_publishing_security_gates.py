"""
Security & Negative Integration Tests for GTA 6 AI Shorts Automation Agent:
Verifies publishing authorization gates, fail-closed semantic analysis,
evidence-based rights verification, physical media ffprobe inspection,
and silent audio detection.
"""

import os
import sys
import uuid
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    config,
    YouTubeSettings,
    PublishingSettings,
    SemanticAnalysisSettings,
    PipelineSettings,
)
from database.db import db
from modules.pipeline import pipeline
from modules.source_discovery import source_discovery, SourceDiscoveryService
from modules.publishing_policy import publishing_policy, PublishingPolicy
from modules.youtube_uploader import youtube_uploader
from modules.voice_generator import voice_generator, VoiceoverResult, TimedWord
from modules.clip_generator import clip_generator
from modules.video_analyzer import SegmentAnalysis
import cli


class TestPublishingSecurityGates(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        uid = uuid.uuid4().hex[:8]
        self.video_id = db.insert_gameplay(
            filename=f"sec_gate_{uid}.mp4",
            filepath=str(self.temp_path / f"sec_gate_{uid}.mp4"),
            file_size=600000,
            duration=30.0,
            resolution_w=1080,
            resolution_h=1920,
            fps=30.0,
            checksum=f"chk_sec_{uid}",
        )
        self.clip_id = db.insert_clip(
            video_id=self.video_id,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=92.0,
            status="pending_review",
            is_fallback=0,
            semantic_status="SUCCESS",
        )

        # Create a valid dummy final video file
        self.final_video_file = self.temp_path / f"final_sec_{uid}.mp4"
        self.final_video_file.write_bytes(b"TEST_VIDEO_BYTES_SEC_GATE")
        db.update_clip_status(self.clip_id, "pending_review", final_path=str(self.final_video_file))

        db.insert_or_update_metadata(
            clip_id=self.clip_id,
            title_recommended="Insane GTA 6 Stunt in Vice City #Shorts",
            titles=["Title 1", "Title 2", "Title 3"],
            description="Epic GTA 6 moment",
            hashtags=["#GTA6", "#Gaming"],
            tags=["GTA 6", "Gaming"],
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # 1. Unapproved clips rejected by upload command
    def test_unapproved_clip_rejected_by_upload(self):
        # Clip starts with approved_for_upload == 0
        clip_data = db.get_clip_by_id(self.clip_id)
        self.assertEqual(clip_data.get("approved_for_upload"), 0)

        # Attempt to publish unapproved clip (enforce_approval defaults to True)
        res = pipeline.approve_and_publish_clip(
            clip_id=self.clip_id,
            privacy_status="private",
            simulate=True,
        )
        self.assertFalse(res["success"])
        self.assertIn("rejected by publishing authorization gate", res["error_message"].lower())

        # Clip must NOT have been self-approved by the failed attempt
        clip_after = db.get_clip_by_id(self.clip_id)
        self.assertEqual(clip_after.get("approved_for_upload"), 0)
        self.assertNotEqual(clip_after.get("status"), "approved")

        # Explicit human approval
        pipeline.approve_clip(self.clip_id)
        clip_approved = db.get_clip_by_id(self.clip_id)
        self.assertEqual(clip_approved.get("approved_for_upload"), 1)
        self.assertEqual(clip_approved.get("status"), "approved")

        # Upload now succeeds
        res_ok = pipeline.approve_and_publish_clip(
            clip_id=self.clip_id,
            privacy_status="private",
            simulate=True,
            enforce_approval=True,
        )
        self.assertTrue(res_ok["success"])

    # 2. CLI upload command requires prior approval
    def test_cli_upload_requires_prior_approval(self):
        # Unapproved clip
        args_unapproved = MagicMock()
        args_unapproved.clip_id = self.clip_id
        args_unapproved.privacy = "private"
        args_unapproved.simulate = True

        with self.assertRaises(SystemExit) as cm:
            cli.cmd_upload(args_unapproved)
        self.assertEqual(cm.exception.code, 1)

        # Now approve via CLI command
        args_approve = MagicMock()
        args_approve.clip_id = self.clip_id
        cli.cmd_approve(args_approve)

        # Clip is now approved
        clip = db.get_clip_by_id(self.clip_id)
        self.assertEqual(clip.get("approved_for_upload"), 1)

    # 3. Rights verification rejects missing or fabricated evidence
    def test_rights_verification_rejects_missing_or_fabricated_evidence(self):
        service = SourceDiscoveryService()

        # A) Registering source with empty/no evidence must not set permission_verified
        res_no_ev = service.register_authorized_source(
            title="Unverified B-Roll",
            license_type="CC-BY",
            creator_name="RandomGamer",
            source_url=None,
        )
        self.assertFalse(res_no_ev["permission_verified"])

        # B) Generic placeholder URL without human verification must be rejected
        res_placeholder = service.register_authorized_source(
            title="Placeholder Source",
            license_type="CC-BY",
            creator_name="SomeCreator",
            source_url="https://creativecommons.org/licenses/",
            human_verified=False,
        )
        self.assertFalse(res_placeholder["permission_verified"])

        # C) verify_rights rejects placeholder URLs
        ev_placeholder = {
            "evidence_type": "CREATIVE_COMMONS_VERIFIED",
            "commercial_reuse_allowed": True,
            "creator_identity": "CCArtist",
            "evidence_url_or_doc": "https://creativecommons.org/licenses/",
        }
        res_ev = service.verify_rights(source_id_or_metadata=None, evidence=ev_placeholder, human_verified=False)
        self.assertFalse(res_ev["verified"])
        self.assertIn("Placeholder or generic", res_ev["error"])

        # D) Explicit human verification approves the source
        source_id = res_placeholder["source_id"]
        man_res = service.manual_verify_source(source_id, notes="Manually reviewed legal permit")
        self.assertTrue(man_res["verified"])
        src_row = db.get_source_by_id(source_id)
        self.assertEqual(src_row["permission_verified"], 1)

    # 4. Fail-closed semantic analysis
    def test_missing_and_fallback_semantic_fails_closed(self):
        # Clip with completely missing semantic analysis
        clip_missing_semantic = {
            "id": self.clip_id,
            "engagement_score": 92.0,
            "duration": 30.0,
            # No is_fallback, no semantic_status, no semantic_score
        }
        res_missing = publishing_policy.evaluate(
            clip=clip_missing_semantic,
            source_verified=True,
            metadata={"title": "T", "description": "D", "tags": ["tag1"]},
        )
        self.assertFalse(res_missing.can_publish)
        self.assertFalse(res_missing.rule_results["semantic_valid_not_fallback"])

        # Clip marked as FAILED semantic status
        clip_failed_semantic = {
            "id": self.clip_id,
            "engagement_score": 92.0,
            "duration": 30.0,
            "semantic_status": "FAILED",
            "is_fallback": 1,
        }
        res_failed = publishing_policy.evaluate(
            clip=clip_failed_semantic,
            source_verified=True,
            metadata={"title": "T", "description": "D", "tags": ["tag1"]},
        )
        self.assertFalse(res_failed.can_publish)
        self.assertFalse(res_failed.rule_results["semantic_valid_not_fallback"])

        # Clip marked as SUCCESS and not fallback
        clip_success_semantic = {
            "id": self.clip_id,
            "engagement_score": 92.0,
            "duration": 30.0,
            "semantic_status": "SUCCESS",
            "is_fallback": 0,
            "semantic_score": 88.0,
            "event_summary": "Authentic police chase",
        }
        res_success = publishing_policy.evaluate(
            clip=clip_success_semantic,
            source_verified=True,
            semantic_is_fallback=False,
            metadata={"title": "T", "description": "D", "tags": ["tag1"]},
        )
        self.assertTrue(res_success.rule_results["semantic_valid_not_fallback"])

    # 5. Physical video and audio ffprobe inspection
    def test_video_spec_ffprobe_duration_and_audio_streams(self):
        policy = PublishingPolicy()

        # Test A: Mock probe where video has no audio stream
        no_audio_spec = {
            "duration": 30.0,
            "width": 1080,
            "height": 1920,
            "has_audio": False,
        }
        dummy_file = self.temp_path / "spec_test.mp4"
        dummy_file.write_bytes(b"dummy_bytes")

        with patch.object(policy, "_probe_media_spec", return_value=no_audio_spec):
            valid, reason = policy.check_video_spec(dummy_file)
            self.assertFalse(valid)
            self.assertIn("lacks required audio stream", reason)

        # Test B: Mock probe where duration is invalid (< 15s)
        short_dur_spec = {
            "duration": 10.0,
            "width": 1080,
            "height": 1920,
            "has_audio": True,
        }
        with patch.object(policy, "_probe_media_spec", return_value=short_dur_spec):
            valid, reason = policy.check_video_spec(dummy_file)
            self.assertFalse(valid)
            self.assertIn("not in [15.0, 60.0]s", reason)

        # Test C: Mock probe where resolution is horizontal (1920x1080 instead of 1080x1920)
        horiz_spec = {
            "duration": 30.0,
            "width": 1920,
            "height": 1080,
            "has_audio": True,
        }
        with patch.object(policy, "_probe_media_spec", return_value=horiz_spec):
            valid, reason = policy.check_video_spec(dummy_file)
            self.assertFalse(valid)
            self.assertIn("not 1080x1920", reason)

        # Test D: Fully compliant video passes
        valid_spec = {
            "duration": 30.0,
            "width": 1080,
            "height": 1920,
            "has_audio": True,
        }
        with patch.object(policy, "_probe_media_spec", return_value=valid_spec):
            valid, reason = policy.check_video_spec(dummy_file)
            self.assertTrue(valid)
            self.assertEqual(reason, "OK")

    # 6. Silent audio voiceover detection
    def test_silent_audio_voiceover_detection(self):
        out_wav = self.temp_path / "silent_test.wav"

        # Force SAPI to fail and fallback to silence
        with patch("win32com.client.Dispatch", side_effect=Exception("SAPI unavailable")):
            dur, timed_words, is_silent, audio_status = voice_generator._synthesize_sapi_fallback(
                "GTA 6 Action Commentary", out_wav
            )
            self.assertTrue(is_silent)
            self.assertEqual(audio_status, "SILENT_FALLBACK")
            self.assertGreater(dur, 0.0)

        # Test generate_voiceover flags silent fallback
        with patch.object(voice_generator, "output_dir", self.temp_path), \
             patch("modules.voice_generator.is_internet_available", return_value=False), \
             patch("win32com.client.Dispatch", side_effect=Exception("SAPI unavailable")):
            res = voice_generator.generate_voiceover(
                clip_id=999,
                language="hinglish",
                include_voiceover=True,
            )
            self.assertTrue(res.is_silent)
            self.assertEqual(res.audio_status, "SILENT_FALLBACK")

    # 7. Environment variable mapping
    def test_config_environment_variable_mapping(self):
        env_overrides = {
            "YOUTUBE_SIMULATION_MODE": "false",
            "YOUTUBE_DEFAULT_PRIVACY": "public",
            "AUTO_PUBLISH": "true",
            "AUTO_PUBLISH_MIN_SCORE": "90.5",
            "OLLAMA_HOST": "http://gpu-server:11434",
            "SEMANTIC_AI_MODEL": "qwen2.5-vl",
        }
        with patch.dict(os.environ, env_overrides):
            yt_settings = YouTubeSettings()
            self.assertFalse(yt_settings.simulate_upload)
            self.assertEqual(yt_settings.default_privacy, "public")
            self.assertTrue(yt_settings.auto_publish)

            pub_settings = PublishingSettings()
            self.assertEqual(pub_settings.min_engagement_score, 90.5)
            self.assertTrue(pub_settings.auto_publish)
            self.assertEqual(pub_settings.default_privacy, "public")

            sem_settings = SemanticAnalysisSettings()
            self.assertEqual(sem_settings.model_name, "qwen2.5-vl")
            self.assertIn("gpu-server", sem_settings.vlm_endpoint)

            pipe_settings = PipelineSettings()
            self.assertTrue(pipe_settings.auto_publish)

    # 8. Clip generator persists semantic status and is_fallback
    def test_clip_generator_persists_semantic_status(self):
        seg = SegmentAnalysis(
            start_time=0.0,
            end_time=25.0,
            duration=25.0,
            visual_excitement=80.0,
            action_intensity=85.0,
            audio_intensity=75.0,
            unpredictability=70.0,
            hook_potential=80.0,
            ending_quality=75.0,
            storytelling_potential=70.0,
            composite_score=82.0,
            tags=["stunt"],
            semantic_score=88.0,
            is_fallback=False,
            semantic_is_fallback=False,
        )
        seg.semantic_status = "SUCCESS"

        with patch.object(clip_generator, "extract_clip", return_value=self.final_video_file):
            cands = clip_generator.generate_candidate_clips(
                video_id=self.video_id,
                input_path=self.final_video_file,
                ranked_segments=[seg],
            )
            self.assertEqual(len(cands), 1)
            cand = cands[0]
            self.assertEqual(cand["semantic_info"]["is_fallback"], False)
            self.assertEqual(cand["semantic_info"]["semantic_status"], "SUCCESS")

            # Check DB record
            db_clip = db.get_clip_by_id(cand["clip_id"])
            self.assertEqual(db_clip.get("is_fallback"), 0)
            self.assertEqual(db_clip.get("semantic_status"), "SUCCESS")


if __name__ == "__main__":
    unittest.main()
