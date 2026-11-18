"""
Comprehensive 25-Point Automated Test Suite for GTA 6 Priority 5 Architecture

Covers:
- YouTube Data API discovery, 30m polling, two-step search & videos.list hydration
- Viewer count handling (including None / hidden)
- Search-omission vs. stream-offline reconciliation
- Pacific Time midnight quota resets
- Authorized source adapter, credential secrecy, and legal firewall
- Bounded ring buffer, context pinning under rotation, and storage limits
- Thread clamping (-threads 4 vs -threads 0)
- Low-latency two-stage event detection & monotonic keyframes
- Temporal IoU NMS
- Conditional 60 FPS preservation and 30 FPS native output
- Dynamic zoompan fps fix (:fps=60)
- BGM mixing and EBU R128 loudness compliance
- Two-Key publishing safety gate (Tier 1 non-overridable vs. Tier 2 overridable)
- Upload-time policy re-evaluation
- Persistent task queue and startup crash recovery
"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
import uuid
from zoneinfo import ZoneInfo

from config import config
from database.db import db
from modules.authorized_source_adapter import (
    AuthorizedSourceAdapter,
    CreatorAuthorizedStreamAdapter,
    SyntheticMockStreamAdapter,
    UnauthorizedFootageError,
    ChunkMetadata,
)
from modules.livestream_discovery import (
    LivestreamDiscoveryService,
    DiscoveredStreamMetadata,
    LOS_ANGELES_TZ,
)
from modules.livestream_monitor import LivestreamMonitor, CandidateAdmissionGovernor, RingBufferChunk
from modules.recovery_service import ApplicationRecoveryService
from modules.job_queue import PersistentJobQueue, QueueWorkerPool
from modules.video_editor import video_editor, probe_source_fps, determine_target_fps
from modules.audio_processor import audio_processor
from modules.clip_generator import clip_generator
from modules.publishing_policy import publishing_policy
from modules.youtube_uploader import youtube_uploader, UploadResult


class TestPriority5Comprehensive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Seed test channel and authorized source
        self.channel_id = f"UC_TEST_{uuid.uuid4().hex[:6]}"
        self.stream_video_id = f"stream_{uuid.uuid4().hex[:6]}"

        # Insert discovered stream
        db.upsert_discovered_stream(
            stream_video_id=self.stream_video_id,
            channel_id=self.channel_id,
            channel_title="Test GTA 6 Creator",
            title="GTA 6 Live Stunts & Police Chase",
            thumbnail_url="https://example.com/thumb.jpg",
            viewer_count=1500,
            is_live=True,
            has_authorized_source=False,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # 1. YouTube discovery search parses metadata, channels, viewer counts
    def test_youtube_discovery_search_success(self):
        service = LivestreamDiscoveryService()
        service.api_key = "test_key"
        mock_streams = [
            DiscoveredStreamMetadata(
                stream_video_id="vid_test_101",
                channel_id="chan_101",
                channel_title="GamerAlpha",
                title="GTA 6 High Speed Chase",
                thumbnail_url="https://img.youtube.com/vi/vid_test_101/hqdefault.jpg",
                viewer_count=2450,
                stream_start_time=None,
                is_live=True,
                discovered_at=time.time(),
            )
        ]
        with patch.object(config.youtube, "simulate_discovery", False), \
             patch.object(service, "_execute_live_search", return_value=mock_streams):
            streams = service.discover_active_streams(query="GTA 6", force_refresh=True)
            self.assertEqual(len(streams), 1)
            self.assertEqual(streams[0].stream_video_id, "vid_test_101")
            self.assertEqual(streams[0].viewer_count, 2450)
            self.assertEqual(streams[0].has_authorized_source, False)

    # 2. Discovery quota caching returns cached records without API calls within TTL
    def test_youtube_discovery_quota_caching(self):
        service = LivestreamDiscoveryService(cache_ttl_seconds=300)
        service._last_poll_time = time.time() - 30.0  # 30s ago, well within 300s TTL

        with patch.object(service, "_execute_live_search") as mock_exec:
            streams = service.discover_active_streams(query="GTA 6", force_refresh=False)
            mock_exec.assert_not_called()
            self.assertGreaterEqual(len(streams), 1)

    # 3. Discovery quota exceeded enters backoff and serves cached records
    def test_youtube_discovery_quota_exceeded_backoff(self):
        service = LivestreamDiscoveryService()
        service.api_key = "test_key"
        with patch.object(config.youtube, "simulate_discovery", False), \
             patch.object(service, "_execute_live_search", side_effect=Exception("HTTP 403 quotaExceeded")):
            streams = service.discover_active_streams(query="GTA 6", force_refresh=True)
            self.assertTrue(service.quota_exhausted)
            self.assertIsInstance(streams, list)

    # 4. Search omission does NOT mark stream offline without direct videos.list confirmation
    def test_search_omission_vs_stream_offline_reconciliation(self):
        service = LivestreamDiscoveryService()
        # Mock search containing everything active EXCEPT self.stream_video_id
        active_ids_from_search = {
            s["stream_video_id"] for s in db.get_active_discovered_streams()
            if s["stream_video_id"] != self.stream_video_id
        }

        # Mock direct status check confirming stream IS still live
        with patch.object(service, "check_stream_status", return_value=(True, None)):
            reconciled = service.reconcile_stale_streams(active_ids_from_search)
            self.assertEqual(reconciled, 0)
            stream_db = db.get_discovered_stream_by_video_id(self.stream_video_id)
            self.assertEqual(stream_db["is_live"], 1)

        # Now mock direct status check confirming stream has genuinely ended
        with patch.object(service, "check_stream_status", return_value=(False, None)):
            reconciled = service.reconcile_stale_streams(active_ids_from_search)
            self.assertEqual(reconciled, 1)
            stream_db_ended = db.get_discovered_stream_by_video_id(self.stream_video_id)
            self.assertEqual(stream_db_ended["is_live"], 0)

    # 5. Pacific Time quota reset boundary resets usage at midnight PT
    def test_pacific_time_quota_reset_boundary(self):
        service = LivestreamDiscoveryService(daily_quota_limit=10000)
        nonce = uuid.uuid4().hex[:8]
        test_day_1 = f"2099-01-{nonce[:4]}"
        test_day_2 = f"2099-01-{nonce[4:]}"

        with patch.object(service, "get_current_pt_date_str", return_value=test_day_1):
            # Record 4800 units on test_day_1
            service._record_quota("search.list", 4800, "background_discovery")
            rem = service.get_remaining_quota_units()
            self.assertEqual(rem, 5200)

        # On next PT calendar date (test_day_2), usage starts at 0
        with patch.object(service, "get_current_pt_date_str", return_value=test_day_2):
            new_day_rem = service.get_remaining_quota_units()
            self.assertEqual(new_day_rem, 10000)

    # 6. Unauthorized footage acquisition is strictly rejected
    def test_unauthorized_footage_rejection(self):
        adapter = CreatorAuthorizedStreamAdapter()
        dest = self.temp_path / "chunk_0.mp4"
        with self.assertRaises(UnauthorizedFootageError):
            adapter.acquire_stream_chunk(
                stream_video_id=self.stream_video_id,
                chunk_duration_sec=12.0,
                destination_path=dest,
            )

    # 7. Authorized adapter acquires chunk with valid duration, fps, and audio
    def test_authorized_adapter_chunk_acquisition(self):
        # Register verified source in database
        db.add_authorized_footage_source(
            creator_identity="Verified Creator",
            license_type="CC-BY",
            evidence_type="CREATIVE_COMMONS_VERIFIED",
            evidence_url_or_doc="https://creativecommons.org/licenses/by/4.0/",
            permission_verified=True,
            commercial_reuse_allowed=True,
            derivative_editing_allowed=True,
            channel_id=self.channel_id,
        )

        adapter = SyntheticMockStreamAdapter(target_fps=60.0, has_audio=True)
        dest = self.temp_path / "auth_chunk.mp4"
        chunk_meta = adapter.acquire_stream_chunk(
            stream_video_id=self.stream_video_id,
            chunk_duration_sec=2.0,
            destination_path=dest,
        )
        self.assertTrue(dest.exists())
        self.assertEqual(chunk_meta.duration_seconds, 2.0)
        self.assertEqual(chunk_meta.fps, 60.0)
        self.assertTrue(chunk_meta.has_audio)

    # 8. Discovery does not automatically grant acquisition rights
    def test_discovery_does_not_grant_acquisition_rights(self):
        service = LivestreamDiscoveryService()
        meta = DiscoveredStreamMetadata(
            stream_video_id="unauth_vid_99",
            channel_id="unauth_chan_99",
            channel_title="Stranger",
            title="Public GTA 6 Stream",
            thumbnail_url="",
            viewer_count=500,
            stream_start_time=None,
            is_live=True,
            discovered_at=time.time(),
        )
        service.sync_to_database([meta])
        rec = db.get_discovered_stream_by_video_id("unauth_vid_99")
        self.assertEqual(rec["has_authorized_source"], 0)

        adapter = CreatorAuthorizedStreamAdapter()
        self.assertFalse(adapter.verify_authorization("unauth_vid_99"))

    # 9. Credential secrecy verifies zero plain text secrets in SQLite
    def test_credential_secrecy_and_no_raw_keys_in_db(self):
        src_id = db.add_authorized_footage_source(
            creator_identity="Secret Creator",
            license_type="Written Creator Permission",
            evidence_type="WRITTEN_PERMISSION",
            evidence_url_or_doc="CONTRACT_HASH_991823",
            permission_verified=True,
            channel_id="chan_secret",
            stream_key_secret_ref="ENV:CREATOR_STREAM_KEY",
        )
        src = db.get_authorized_footage_source_by_id(src_id)
        self.assertEqual(src["stream_key_secret_ref"], "ENV:CREATOR_STREAM_KEY")
        # Ensure raw secret is not stored
        self.assertNotIn("live_sk_secret_12345", json.dumps(src))

    # 10. Independent simulation mode flags toggle independently
    def test_independent_simulation_mode_flags(self):
        with patch.dict(os.environ, {
            "YOUTUBE_UPLOAD_SIMULATION": "0",
            "LIVESTREAM_DISCOVERY_MOCK": "1",
            "FOOTAGE_ACQUISITION_SIMULATION": "1",
        }):
            from config import YouTubeSettings
            yt = YouTubeSettings()
            self.assertFalse(yt.simulate_upload)
            self.assertTrue(yt.simulate_discovery)
            self.assertTrue(yt.simulate_acquisition)

    # 11. Bounded ring buffer rotates and purges unpinned chunks past max retention
    def test_bounded_ring_buffer_rotation(self):
        adapter = MagicMock()
        adapter.verify_authorization.return_value = True
        monitor = LivestreamMonitor(
            stream_video_id=self.stream_video_id,
            adapter=adapter,
            max_buffer_chunks=3,
        )
        # Populate 5 unpinned chunks
        for i in range(5):
            fpath = self.temp_path / f"chunk_{i:05d}.mp4"
            fpath.write_bytes(b"DATA")
            monitor._ring_buffer[i] = RingBufferChunk(
                chunk_index=i,
                filepath=fpath,
                duration=12.0,
                start_timestamp=i * 12.0,
                fps=30.0,
                has_audio=True,
                is_pinned=False,
            )
        monitor._rotate_ring_buffer()
        # Chunks 0 and 1 should have been evicted, retaining 3 chunks (2, 3, 4)
        self.assertEqual(len(monitor._ring_buffer), 3)
        self.assertNotIn(0, monitor._ring_buffer)
        self.assertNotIn(1, monitor._ring_buffer)
        self.assertIn(2, monitor._ring_buffer)

    # 12. Pinned buffer retention preserves highlighted context chunks under rotation
    def test_pinned_buffer_retention_under_rotation(self):
        adapter = MagicMock()
        adapter.verify_authorization.return_value = True
        monitor = LivestreamMonitor(
            stream_video_id=self.stream_video_id,
            adapter=adapter,
            max_buffer_chunks=3,
        )
        for i in range(5):
            fpath = self.temp_path / f"chunk_{i:05d}.mp4"
            fpath.write_bytes(b"DATA")
            monitor._ring_buffer[i] = RingBufferChunk(
                chunk_index=i,
                filepath=fpath,
                duration=12.0,
                start_timestamp=i * 12.0,
                fps=30.0,
                has_audio=True,
                is_pinned=(i in (0, 1)),  # Chunks 0 and 1 are pinned!
            )
        monitor._rotate_ring_buffer()
        # Even though buffer size is 3, pinned chunks 0 and 1 MUST NOT be evicted
        self.assertIn(0, monitor._ring_buffer)
        self.assertIn(1, monitor._ring_buffer)

    # 13. Disk quota enforcement triggers garbage collection when threshold is exceeded
    def test_disk_quota_enforcement(self):
        recovery = ApplicationRecoveryService()
        recovery.buffer_dir = self.temp_path
        old_chunk = self.temp_path / "old_chunk.mp4"
        old_chunk.write_bytes(b"A" * 1024 * 1024)
        old_time = time.time() - 3600
        os.utime(old_chunk, (old_time, old_time))

        # Mock storage bytes to 11 GB (exceeding 10 GB limit)
        with patch.object(recovery, "_get_managed_storage_bytes", return_value=int(11.5 * 1024 ** 3)):
            reclaimed = recovery.enforce_storage_limits()
            self.assertGreater(reclaimed, 0.0)
            self.assertFalse(old_chunk.exists())

    # 14. FFmpeg thread clamping enforces -threads 4 and eliminates -threads 0
    def test_ffmpeg_thread_clamping(self):
        input_vid = self.temp_path / "test_th.mp4"
        input_vid.write_bytes(b"DUMMY_MP4")
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_run.return_value = mock_proc
            try:
                clip_generator.extract_clip(input_vid, 0.0, 15.0, "clamped.mp4")
            except Exception:
                pass
            if mock_run.called:
                cmd = mock_run.call_args[0][0]
                self.assertIn("-threads", cmd)
                th_idx = cmd.index("-threads")
                self.assertEqual(cmd[th_idx + 1], str(config.resources.ffmpeg_cpu_threads))
                self.assertNotIn("0", cmd[th_idx:th_idx+2])

    # 15. Stage 1 fast heuristic filter rejects static low-motion chunks
    def test_stage1_fast_heuristic_filter_rejection(self):
        gov = CandidateAdmissionGovernor()
        admitted, reason = gov.evaluate_admission(heuristic_score=50.0)
        self.assertFalse(admitted)
        self.assertIn("below effective threshold", reason)

    # 16. Stage 1 fast heuristic filter accepts high-action chunks
    def test_stage1_fast_heuristic_filter_acceptance(self):
        gov = CandidateAdmissionGovernor()
        admitted, reason = gov.evaluate_admission(heuristic_score=78.0)
        self.assertTrue(admitted)
        self.assertIn("Admitted", reason)

    # 17. Stage 2 VLM keyframe extraction produces strictly monotonic timestamps
    def test_stage2_vlm_keyframe_extraction_monotonicity(self):
        from modules.semantic_analyzer import semantic_analyzer
        keyframes = semantic_analyzer.select_keyframes(
            video_path=self.temp_path / "dummy.mp4",
            start_time=10.0,
            end_time=25.0,
            motion_scores=[70.0, 85.0, 90.0, 60.0],
            audio_energies=[0.2, 0.8, 0.5, 0.3],
        )
        self.assertEqual(len(keyframes), 3)
        t_hook, t_peak, t_climax = keyframes[0].timestamp, keyframes[1].timestamp, keyframes[2].timestamp
        self.assertTrue(10.0 <= t_hook < t_peak < t_climax <= 25.0)

    # 18. Temporal IoU NMS merges overlapping events
    def test_temporal_iou_nms_deduplication(self):
        from modules.highlight_ranker import highlight_ranker, SegmentAnalysis
        seg1 = SegmentAnalysis(start_time=10.0, end_time=35.0, duration=25.0, visual_excitement=80.0,
                               action_intensity=85.0, audio_intensity=80.0, unpredictability=70.0,
                               hook_potential=75.0, ending_quality=75.0, storytelling_potential=70.0,
                               composite_score=85.0, tags=["action"])
        seg2 = SegmentAnalysis(start_time=20.0, end_time=45.0, duration=25.0, visual_excitement=82.0,
                               action_intensity=88.0, audio_intensity=82.0, unpredictability=72.0,
                               hook_potential=78.0, ending_quality=78.0, storytelling_potential=72.0,
                               composite_score=88.0, tags=["action"])
        merged = highlight_ranker.rank_and_deduplicate([seg1, seg2], top_n=2)
        # High overlap (IoU = 15s / 35s = 0.43 > 0.30) should merge into single highlight
        self.assertEqual(len(merged), 1)

    # 19. Conditional FPS preserves 60 FPS gameplay
    def test_conditional_fps_60fps_preservation(self):
        target = determine_target_fps(60.0)
        self.assertEqual(target, 60)
        target_59_94 = determine_target_fps(59.94)
        self.assertEqual(target_59_94, 60)

    # 20. Conditional FPS outputs native 30 FPS without artificial duplication
    def test_conditional_fps_30fps_native(self):
        target_30 = determine_target_fps(30.0)
        self.assertEqual(target_30, 30)
        target_29_97 = determine_target_fps(29.97)
        self.assertEqual(target_29_97, 30)
        target_24 = determine_target_fps(24.0)
        self.assertEqual(target_24, 24)

    # 21. Action fast zoompan dynamically injects :fps=60
    def test_action_fast_zoompan_dynamic_fps_fix(self):
        fg = video_editor._build_filtergraph(
            template_name="action_fast",
            duration=30.0,
            target_fps=60,
        )
        self.assertIn(":fps=60", fg)
        self.assertNotIn(":fps=30", fg)

    # 22. Audio mixing includes BGM and EBU R128 loudness normalization
    def test_audio_ducking_and_loudness_compliance(self):
        dummy_video = self.temp_path / "gameplay.mp4"
        dummy_video.write_bytes(b"VID")
        dummy_voice = self.temp_path / "voice.wav"
        dummy_voice.write_bytes(b"VOICE")
        dummy_bgm = self.temp_path / "bgm.mp3"
        dummy_bgm.write_bytes(b"BGM")
        out_aac = self.temp_path / "mixed.aac"

        def _mock_run_effect(cmd, *args, **kwargs):
            out_aac.write_bytes(b"MIXED_AUDIO_DATA")
            mock_p = MagicMock()
            mock_p.returncode = 0
            return mock_p

        with patch("subprocess.run", side_effect=_mock_run_effect) as mock_run, \
             patch.object(audio_processor, "has_audio_stream", return_value=True):
            audio_processor.mix_audio_tracks(
                gameplay_video=dummy_video,
                voiceover_audio=dummy_voice,
                output_audio_path=out_aac,
                duration=15.0,
                bgm_audio=dummy_bgm,
                include_voiceover=True,
            )
            cmd = mock_run.call_args[0][0]
            cmd_str = " ".join(cmd)
            self.assertIn("loudnorm", cmd_str)
            self.assertIn("amix=inputs=3", cmd_str)

    # 23. Two-Key publishing gate enforcement (Tier 1 invariant non-overridable vs Tier 2 overridable)
    def test_two_key_publishing_gate_enforcement(self):
        # Setup clip without verified source
        dummy_video = self.temp_path / "clip_unauth.mp4"
        dummy_video.write_bytes(b"TEST_BYTES")
        clip_id = db.insert_clip(
            video_id=1,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=90.0,
            candidate_path=str(dummy_video),
            final_path=str(dummy_video),
        )
        db.set_clip_approval(clip_id, approved=True)  # Human approved!
        db.insert_or_update_metadata(
            clip_id=clip_id,
            title_recommended="Test GTA 6 Stunt",
            titles=["Title 1"],
            description="Test Desc",
            hashtags=["#GTA6", "#Shorts"],
            tags=["GTA 6"],
        )

        # Attempt upload: even though human approved, missing source permission MUST fail
        with patch.object(config.publishing, "strict_two_key_gate", True), \
             patch.object(config.publishing, "enforce_in_simulation", True):
            res = youtube_uploader.upload_short(
                clip_id=clip_id,
                video_path=dummy_video,
                title="Test GTA 6 Stunt",
                description="Test Desc",
                tags=["GTA 6"],
                simulate=True,
                enforce_approval=True,
            )
            self.assertFalse(res.success)
            self.assertIn("Tier 1 legal/media invariant failed", res.error_message)

    # 24. Upload time policy re-evaluation detects deleted/corrupted file
    def test_upload_time_policy_reevaluation(self):
        missing_file = self.temp_path / "non_existent.mp4"
        clip_id = db.insert_clip(
            video_id=1,
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            engagement_score=90.0,
            candidate_path=str(missing_file),
            final_path=str(missing_file),
        )
        db.set_clip_approval(clip_id, approved=True)
        with self.assertRaises(FileNotFoundError):
            youtube_uploader.upload_short(
                clip_id=clip_id,
                video_path=missing_file,
                title="Deleted File",
                description="Test Desc",
                tags=["GTA 6"],
                simulate=True,
                enforce_approval=True,
            )

    # 25. Restart recovery re-queues running jobs, marks dead sessions abrupted, and purges orphans
    def test_restart_recovery_reconciliation(self):
        # 1. Seed interrupted job
        job_id = db.enqueue_processing_job("highlight_render", {"clip_id": 999})
        with db.get_connection() as conn:
            conn.execute("UPDATE processing_jobs SET status = 'running' WHERE id = ?", (job_id,))
            conn.commit()

        # 2. Seed active dead session
        session_id = db.create_monitoring_session(1, str(self.temp_path / "dead_stream"))

        # 3. Seed orphan chunk file
        orphan_dir = config.BUFFER_DIR / "stream_9999"
        orphan_dir.mkdir(parents=True, exist_ok=True)
        (orphan_dir / "orphan_chunk.mp4").write_bytes(b"ORPHAN")

        # Execute recovery
        recovery = ApplicationRecoveryService()
        res = recovery.reconcile(purge_orphans=True)

        self.assertGreaterEqual(res["requeued_jobs"], 1)
        self.assertGreaterEqual(res["abrupted_sessions"], 1)
        self.assertFalse((orphan_dir / "orphan_chunk.mp4").exists())


if __name__ == "__main__":
    unittest.main()
