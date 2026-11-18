"""
Integration & Reliability Tests for Milestone Priority 3:
Publishing Engine, Rights Verification, Fallback Handling, and Reliability Hardening.
"""

import sys
import uuid
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from database.db import db
from modules.video_analyzer import SegmentAnalysis
from modules.semantic_analyzer import semantic_analyzer, SemanticAnalysisResult
from modules.highlight_ranker import highlight_ranker
from modules.source_discovery import source_discovery
from modules.publishing_policy import publishing_policy
from modules.youtube_uploader import youtube_uploader
from modules.voice_generator import voice_generator


class TestPublishingAndHardening(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        uid = uuid.uuid4().hex[:8]
        self.video_id = db.insert_gameplay(
            filename=f"test_hardening_{uid}.mp4",
            filepath=str(self.temp_path / f"test_hardening_{uid}.mp4"),
            file_size=500000,
            duration=30.0,
            resolution_w=1080,
            resolution_h=1920,
            fps=30.0,
            checksum=f"chk_{uid}",
        )
        self.clip_id = db.insert_clip(
            video_id=self.video_id,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=90.0,
            status="pending_review",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rights_verification_workflow(self):
        # 1. Valid rights evidence
        valid_ev = {
            "evidence_type": "USER_ORIGINAL_FOOTAGE",
            "commercial_reuse_allowed": True,
            "creator_identity": "LeadEditor42",
            "evidence_url_or_doc": "https://creator.portal/proof/123",
        }
        res = source_discovery.verify_rights(source_id_or_metadata=None, evidence=valid_ev)
        self.assertTrue(res["verified"])
        self.assertEqual(res["evidence_type"], "USER_ORIGINAL_FOOTAGE")

        # 2. Rejection without evidence
        res_no_ev = source_discovery.verify_rights(source_id_or_metadata=None, evidence=None)
        self.assertFalse(res_no_ev["verified"])
        self.assertIn("Missing evidence", res_no_ev["error"])

        # 3. Rejection when commercial reuse is disallowed
        non_comm_ev = {
            "evidence_type": "CREATIVE_COMMONS_VERIFIED",
            "commercial_reuse_allowed": False,
            "creator_identity": "CCArtist",
            "evidence_url_or_doc": "https://cc.org/non-comm",
        }
        res_non_comm = source_discovery.verify_rights(source_id_or_metadata=None, evidence=non_comm_ev)
        self.assertFalse(res_non_comm["verified"])
        self.assertIn("Commercial reuse is not permitted", res_non_comm["error"])

        # 4. Rejection with invalid evidence type
        invalid_type_ev = {
            "evidence_type": "UNVERIFIED_INTERNET_DOWNLOAD",
            "commercial_reuse_allowed": True,
            "creator_identity": "Anon",
            "evidence_url_or_doc": "https://random.link",
        }
        res_inv = source_discovery.verify_rights(source_id_or_metadata=None, evidence=invalid_type_ev)
        self.assertFalse(res_inv["verified"])
        self.assertIn("Invalid evidence type", res_inv["error"])

        # 5. String 'false' in commercial reuse must be rejected
        str_false_ev = {
            "evidence_type": "CREATIVE_COMMONS_VERIFIED",
            "commercial_reuse_allowed": "false",
            "creator_identity": "Gamer",
            "evidence_url_or_doc": "https://cc.org/doc",
        }
        res_str_f = source_discovery.verify_rights(source_id_or_metadata=None, evidence=str_false_ev)
        self.assertFalse(res_str_f["verified"])

        # 6. Unicode creator identity & international URLs
        unicode_ev = {
            "evidence_type": "USER_ORIGINAL_FOOTAGE",
            "commercial_reuse_allowed": True,
            "creator_identity": "गौतम_गेमिंग🎮",
            "evidence_url_or_doc": "https://více-cìty.example.com/proof?id=123",
        }
        res_uni = source_discovery.verify_rights(source_id_or_metadata=None, evidence=unicode_ev)
        self.assertTrue(res_uni["verified"])
        self.assertEqual(res_uni["creator_identity"], "गौतम_गेमिंग🎮")

    def test_fallback_score_exclusion_in_highlight_ranker(self):
        seg = SegmentAnalysis(
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            visual_excitement=70.0,
            action_intensity=80.0,
            audio_intensity=75.0,
            unpredictability=60.0,
            hook_potential=65.0,
            ending_quality=70.0,
            storytelling_potential=70.0,
            composite_score=72.5,
            tags=["action"],
            semantic_score=99.0,  # Artificially high fallback score
            is_fallback=True,
            semantic_is_fallback=True,
        )

        # When is_fallback is True, score should be the CV/audio composite (72.5), NOT influenced by 99.0
        score = highlight_ranker.calculate_semantic_ranking_score(seg)
        self.assertEqual(score, 72.5)

        # When is_fallback is False, semantic score influences ranking
        seg.is_fallback = False
        seg.semantic_is_fallback = False
        active_score = highlight_ranker.calculate_semantic_ranking_score(seg)
        self.assertGreater(active_score, 72.5)

    def test_voice_generator_fallback_factual_commentary(self):
        fallback_semantic = {
            "is_fallback": True,
            "event_summary": "GTA 6 gameplay sequence",
            "why_entertaining": "High visual action and dynamic gameplay pacing.",
            "suggested_hook": "Check out this GTA 6 gameplay sequence!",
        }

        # Script must be factual and neutral without hallucinating nonexistent events
        script = voice_generator.assemble_script(
            language="hinglish",
            tags=["action"],
            semantic_info=fallback_semantic,
            is_fallback=True,
        )
        self.assertIn("GTA 6 Vice City", script)
        self.assertIn("gameplay", script)

    def test_vlm_timeout_configuration(self):
        # Verify separate connect and inference timeouts
        self.assertEqual(config.semantic.connect_timeout_seconds, 5.0)
        self.assertGreaterEqual(config.semantic.inference_timeout_seconds, 60.0)
        self.assertEqual(semantic_analyzer.connect_timeout, 5.0)
        self.assertGreaterEqual(semantic_analyzer.inference_timeout, 60.0)

    def test_publishing_policy_evaluation_rules(self):
        # Test low engagement score rejection
        low_score_clip = {
            "id": self.clip_id,
            "engagement_score": 60.0,  # Below 85.0
            "is_fallback": False,
            "duration": 30.0,
        }
        res = publishing_policy.evaluate(
            clip=low_score_clip,
            source_verified=True,
            semantic_is_fallback=False,
            metadata={"title": "Test Title", "description": "Desc", "tags": ["tag1"]},
        )
        self.assertFalse(res.can_publish)
        self.assertEqual(res.status, "pending_review")
        self.assertTrue(any("below threshold" in r for r in res.reasons_failed))

        # Test fallback semantic analysis rejection
        fallback_clip = {
            "id": self.clip_id,
            "engagement_score": 92.0,
            "is_fallback": True,
            "duration": 30.0,
        }
        res_fb = publishing_policy.evaluate(
            clip=fallback_clip,
            source_verified=True,
            semantic_is_fallback=True,
            metadata={"title": "Test Title", "description": "Desc", "tags": ["tag1"]},
        )
        self.assertFalse(res_fb.can_publish)
        self.assertTrue(any("fallback" in r for r in res_fb.reasons_failed))

        # Test unverified source rejection
        res_src = publishing_policy.evaluate(
            clip=low_score_clip,
            source_verified=False,
            semantic_is_fallback=False,
            metadata={"title": "Test Title", "description": "Desc", "tags": ["tag1"]},
        )
        self.assertFalse(res_src.can_publish)
        self.assertTrue(any("permission is not verified" in r for r in res_src.reasons_failed))

        # Test video spec on non-existent and corrupted video
        non_existent = self.temp_path / "does_not_exist.mp4"
        valid_spec, reason = publishing_policy.check_video_spec(non_existent)
        self.assertFalse(valid_spec)
        self.assertIn("does not exist", reason)

        corrupt_vid = self.temp_path / "corrupt.mp4"
        corrupt_vid.write_bytes(b"\x00\x00\x00\x18ftypmp42junkcorruptdata")
        valid_spec_c, reason_c = publishing_policy.check_video_spec(corrupt_vid)
        self.assertFalse(valid_spec_c)

        # Test Mode A clip without verified source is rejected
        mode_a_clip = {
            "id": self.clip_id,
            "video_id": self.video_id,  # video_id in setUp has no source_id
            "engagement_score": 92.0,
            "is_fallback": False,
            "duration": 30.0,
        }
        res_mode_a = publishing_policy.evaluate(
            clip=mode_a_clip,
            semantic_is_fallback=False,
            metadata={"title": "Test Title", "description": "Desc", "tags": ["tag1"]},
        )
        self.assertFalse(res_mode_a.can_publish)
        self.assertFalse(res_mode_a.rule_results["source_permission_verified"])

    def test_authorization_gate_in_uploader(self):
        dummy_file = self.temp_path / "dummy_short.mp4"
        dummy_file.write_bytes(b"short_bytes_content_12345")

        # Unapproved clip with failing policy is rejected when enforce_approval=True
        res = youtube_uploader.upload_short(
            clip_id=self.clip_id,
            video_path=dummy_file,
            title="Unauthorized Short",
            description="Should be rejected",
            tags=["GTA 6"],
            simulate=True,
            enforce_approval=True,
        )
        self.assertFalse(res.success)
        self.assertIn("rejected by publishing authorization gate", res.error_message)

        # After approval, upload is authorized
        db.set_clip_approval(self.clip_id, approved=True)
        res_approved = youtube_uploader.upload_short(
            clip_id=self.clip_id,
            video_path=dummy_file,
            title="Authorized Short",
            description="Should succeed",
            tags=["GTA 6"],
            simulate=True,
            enforce_approval=True,
        )
        self.assertTrue(res_approved.success)


if __name__ == "__main__":
    unittest.main()
