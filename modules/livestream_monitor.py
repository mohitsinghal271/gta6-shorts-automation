"""
Livestream Monitor Module for GTA 6 AI YouTube Shorts Automation Agent

Implements bounded rolling chunk ring buffer with intelligent context pinning,
two-tier candidate admission governance, asynchronous decoupling from AI rendering,
and stream health telemetry.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import shutil
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from config import config
from database.db import db
from modules.authorized_source_adapter import AuthorizedSourceAdapter, ChunkMetadata, UnauthorizedFootageError

logger = logging.getLogger("gta6_agent.monitor")


@dataclass
class RingBufferChunk:
    chunk_index: int
    filepath: Path
    duration: float
    start_timestamp: float
    fps: float
    has_audio: bool
    is_pinned: bool = False
    pinned_by_events: Set[int] = field(default_factory=set)


class CandidateAdmissionGovernor:
    """
    Protects workstation disk and queue limits by regulating candidate admission:
    1. 60-second cooldown per stream (unless emergency score >= 90.0).
    2. Dynamic threshold escalation under burst activity.
    3. Storage-aware shedding under elevated disk pressure.
    4. Hard candidate ceiling of max 50 active candidates.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self.last_admission_time: Optional[float] = None
        self.recent_admission_timestamps: List[float] = []

    def evaluate_admission(self, heuristic_score: float) -> Tuple[bool, str]:
        now = time.time()
        active_count = db.count_active_candidates()

        # Hard ceiling check
        if active_count >= config.resources.max_active_candidates:
            return False, f"Queue ceiling reached: {active_count} active candidates (max {config.resources.max_active_candidates})"

        # Check total storage usage
        buffer_size_gb = self._get_directory_size_gb(config.BUFFER_DIR)
        candidates_size_gb = self._get_directory_size_gb(config.CANDIDATES_DIR)
        total_usage_gb = buffer_size_gb + candidates_size_gb

        if total_usage_gb >= 8.5:
            return False, f"Emergency disk ceiling breached: {total_usage_gb:.2f} GB used (frozen at 8.5 GB)"

        # Prune recent admission timestamps older than 5 minutes
        cutoff = now - 300.0
        self.recent_admission_timestamps = [t for t in self.recent_admission_timestamps if t >= cutoff]
        density = len(self.recent_admission_timestamps)

        # Dynamic threshold escalation
        if density <= 3:
            effective_threshold = 65.0
        elif density == 4:
            effective_threshold = 75.0
        elif density == 5:
            effective_threshold = 82.0
        else:
            effective_threshold = 88.0

        # Elevated disk pressure adjustment
        effective_cooldown = self.cooldown_seconds
        if total_usage_gb >= 7.0:
            effective_threshold = max(effective_threshold, 80.0)
            effective_cooldown = max(effective_cooldown, 120.0)

        # Emergency breakthrough threshold
        if heuristic_score >= 90.0:
            self.last_admission_time = now
            self.recent_admission_timestamps.append(now)
            return True, "Emergency breakthrough score >= 90.0"

        # Cooldown check
        if self.last_admission_time and (now - self.last_admission_time < effective_cooldown):
            return False, f"Suppressed by cooldown ({now - self.last_admission_time:.1f}s < {effective_cooldown}s)"

        # Threshold check
        if heuristic_score < effective_threshold:
            return False, f"Score {heuristic_score:.1f} below effective threshold {effective_threshold:.1f}"

        self.last_admission_time = now
        self.recent_admission_timestamps.append(now)
        return True, f"Admitted (Score {heuristic_score:.1f} >= {effective_threshold:.1f})"

    def _get_directory_size_gb(self, directory: Path) -> float:
        if not directory.exists():
            return 0.0
        total_bytes = sum(f.stat().st_size for f in directory.glob("**/*") if f.is_file())
        return total_bytes / (1024 ** 3)


class LivestreamMonitor:
    """
    Monitors an individual authorized GTA 6 livestream.
    Ingests 10-15s chunks into a bounded ring buffer, executes Stage 1 fast filtering,
    pins context chunks on detected highlights, and asynchronously queues candidates.
    """

    def __init__(
        self,
        stream_video_id: str,
        adapter: AuthorizedSourceAdapter,
        chunk_duration_sec: float = 12.0,
        max_buffer_chunks: int = 5,
    ):
        self.stream_video_id = stream_video_id
        self.adapter = adapter
        self.chunk_duration_sec = chunk_duration_sec
        self.max_buffer_chunks = max_buffer_chunks

        self.stream_record = db.get_discovered_stream_by_video_id(stream_video_id)
        if not self.stream_record:
            raise ValueError(f"Stream '{stream_video_id}' not found in discovered_streams.")

        self.stream_id = self.stream_record["id"]
        self.buffer_dir = config.BUFFER_DIR / f"stream_{self.stream_id}"
        self.buffer_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = db.create_monitoring_session(self.stream_id, str(self.buffer_dir))
        self.governor = CandidateAdmissionGovernor()

        self._ring_buffer: Dict[int, RingBufferChunk] = {}
        self._current_chunk_index = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Starts background monitoring loop in a dedicated worker thread."""
        if not self.adapter.verify_authorization(self.stream_video_id):
            db.update_monitoring_session_status(self.session_id, "error")
            raise UnauthorizedFootageError(
                f"Cannot monitor stream '{self.stream_video_id}': verified rights not found in authorized_footage_sources."
            )

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name=f"Monitor-{self.stream_video_id}")
        self._thread.start()
        logger.info("Started LivestreamMonitor session %d for stream %s", self.session_id, self.stream_video_id)

    def stop(self):
        """Signals the monitoring loop to cleanly conclude."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        db.update_monitoring_session_status(self.session_id, "stopped")
        self.adapter.close()
        logger.info("Stopped LivestreamMonitor session %d", self.session_id)

    def _monitor_loop(self):
        while self._running:
            cycle_start = time.time()
            chunk_idx = self._current_chunk_index
            chunk_file = self.buffer_dir / f"chunk_{chunk_idx:05d}.mp4"
            start_ts = chunk_idx * self.chunk_duration_sec

            try:
                # 1. Acquire discrete chunk from authorized adapter
                metadata = self.adapter.acquire_stream_chunk(
                    stream_video_id=self.stream_video_id,
                    chunk_duration_sec=self.chunk_duration_sec,
                    destination_path=chunk_file,
                    chunk_index=chunk_idx,
                    start_timestamp=start_ts,
                )
                db.increment_session_chunks(self.session_id)

                rb_chunk = RingBufferChunk(
                    chunk_index=chunk_idx,
                    filepath=metadata.filepath,
                    duration=metadata.duration_seconds,
                    start_timestamp=metadata.start_timestamp,
                    fps=metadata.fps,
                    has_audio=metadata.has_audio,
                )
                self._ring_buffer[chunk_idx] = rb_chunk

                # 2. Stage 1: Ultra-Fast Heuristic Evaluation (< 1.5s target)
                h_score, motion_score, audio_score = self._evaluate_stage1(metadata.filepath)

                # 3. Candidate Admission Governance
                admitted, reason = self.governor.evaluate_admission(h_score)
                event_id = db.record_detected_event(
                    session_id=self.session_id,
                    chunk_index=chunk_idx,
                    timestamp_start=start_ts,
                    timestamp_end=start_ts + metadata.duration_seconds,
                    stage1_motion_score=motion_score,
                    stage1_audio_score=audio_score,
                    stage1_heuristic_score=h_score,
                    passed_stage1=admitted,
                )

                if admitted:
                    logger.info("Highlight detected in chunk %d (Score: %.1f). %s", chunk_idx, h_score, reason)
                    db.increment_session_highlights(self.session_id)
                    # 4. Context Pinning (Chunks N-2 through N+2)
                    self._pin_context_chunks(chunk_idx, event_id)
                    # 5. Promote Candidate & Enqueue Asynchronous AI Task
                    self._promote_candidate_async(chunk_idx, event_id, h_score)

                # 6. Evict Old Unpinned Chunks
                self._rotate_ring_buffer()

                # 7. Record Telemetry & Heartbeat
                db.record_stream_health(
                    session_id=self.session_id,
                    bitrate_kbps=metadata.bitrate_kbps,
                    fps=metadata.fps,
                    status="healthy",
                )

            except Exception as e:
                logger.error("Error in stream monitor loop for %s: %s", self.stream_video_id, e)
                db.record_stream_health(session_id=self.session_id, bitrate_kbps=None, fps=None, status="degraded")

            self._current_chunk_index += 1
            # Sleep if cycle finished faster than chunk duration to maintain pacing
            elapsed = time.time() - cycle_start
            sleep_time = max(0.0, self.chunk_duration_sec - elapsed)
            if sleep_time > 0 and self._running:
                time.sleep(min(sleep_time, 2.0))

    def _evaluate_stage1(self, video_path: Path) -> Tuple[float, float, float]:
        """
        Fast heuristic visual and audio difference calculation (< 1.5s).
        Uses downscaled frame difference and audio energy spikes.
        """
        from modules.scene_detector import SceneDetector
        from modules.video_analyzer import VideoAnalyzer

        try:
            # Fast visual motion probe
            detector = SceneDetector(video_path, sample_fps=4)
            scenes = detector.detect_scenes(threshold=28.0)
            motion_score = 75.0 if len(scenes) > 1 else (60.0 if scenes else 40.0)

            # Fast audio RMS probe
            analyzer = VideoAnalyzer(video_path)
            audio_score = 65.0
            if analyzer.has_audio:
                windows = analyzer.analyze_sliding_windows(window_duration=self.chunk_duration_sec, step_size=self.chunk_duration_sec)
                if windows:
                    audio_score = windows[0].audio_score
                    motion_score = max(motion_score, windows[0].motion_score)

            h_score = 0.60 * motion_score + 0.40 * audio_score
            return h_score, motion_score, audio_score
        except Exception:
            return 50.0, 50.0, 50.0

    def _pin_context_chunks(self, center_idx: int, event_id: int):
        """Pins chunks [center_idx - 2 .. center_idx + 2] to preserve full highlight context."""
        for offset in range(-2, 3):
            target_idx = center_idx + offset
            if target_idx in self._ring_buffer:
                self._ring_buffer[target_idx].is_pinned = True
                self._ring_buffer[target_idx].pinned_by_events.add(event_id)

    def unpin_event_chunks(self, event_id: int):
        """Unpins chunks associated with an event after candidate extraction completes."""
        for c in self._ring_buffer.values():
            if event_id in c.pinned_by_events:
                c.pinned_by_events.remove(event_id)
                if not c.pinned_by_events:
                    c.is_pinned = False

    def _promote_candidate_async(self, chunk_idx: int, event_id: int, score: float):
        """Saves candidate clip reference and enqueues asynchronous AI processing task."""
        candidate_filename = f"cand_stream_{self.stream_id}_chunk_{chunk_idx:05d}.mp4"
        candidate_path = config.CANDIDATES_DIR / candidate_filename
        source_chunk = self.buffer_dir / f"chunk_{chunk_idx:05d}.mp4"

        if source_chunk.exists():
            shutil.copy2(source_chunk, candidate_path)

        pinned_indices = [
            i for i in range(chunk_idx - 2, chunk_idx + 3) if i in self._ring_buffer
        ]
        cand_id = db.add_highlight_candidate(
            session_id=self.session_id,
            start_time=chunk_idx * self.chunk_duration_sec,
            end_time=(chunk_idx + 1) * self.chunk_duration_sec,
            duration=self.chunk_duration_sec,
            composite_engagement_score=score,
            pinned_chunk_indices=pinned_indices,
            candidate_video_path=str(candidate_path),
            event_id=event_id,
        )

        # Enqueue background task for worker pool
        db.enqueue_processing_job(
            job_type="vlm_inference",
            payload={
                "candidate_id": cand_id,
                "event_id": event_id,
                "candidate_path": str(candidate_path),
                "stream_id": self.stream_id,
                "session_id": self.session_id,
            },
            priority=5,
        )

    def _rotate_ring_buffer(self):
        """Evicts oldest unpinned chunks when ring buffer exceeds retention limit."""
        sorted_indices = sorted(self._ring_buffer.keys())
        while len(sorted_indices) > self.max_buffer_chunks:
            oldest_idx = sorted_indices[0]
            chunk = self._ring_buffer[oldest_idx]
            if chunk.is_pinned:
                # Pinned chunks are immune to eviction
                sorted_indices.pop(0)
                continue

            # Unpinned chunk is safely deleted
            if chunk.filepath.exists():
                try:
                    chunk.filepath.unlink()
                except Exception:
                    pass
            del self._ring_buffer[oldest_idx]
            sorted_indices.pop(0)
