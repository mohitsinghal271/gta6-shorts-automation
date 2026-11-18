"""
Persistent Task Queue & Background Worker Pool for GTA 6 AI Shorts Platform

Provides SQLite-backed, durable task processing to prevent memory bloat and
decouple stream ingestion from heavy AI inference and FFmpeg video encoding.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable

from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.job_queue")


class PersistentJobQueue:
    """Interface to persistent SQLite task queue in processing_jobs."""

    def enqueue(self, job_type: str, payload: Dict[str, Any], priority: int = 10, max_retries: int = 3) -> int:
        return db.enqueue_processing_job(job_type, payload, priority, max_retries)

    def acquire_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        return db.acquire_next_processing_job(worker_id)

    def complete(self, job_id: int, result: Optional[Dict[str, Any]] = None):
        db.complete_processing_job(job_id, result)

    def fail(self, job_id: int, error_message: str):
        db.fail_processing_job(job_id, error_message)

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        return db.get_processing_job_by_id(job_id)


class QueueWorkerPool:
    """
    Manages a bounded pool of background worker threads consuming tasks from processing_jobs.
    Executes VLM inference, voice synthesis, video rendering, and publishing asynchronously.
    """

    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.queue = PersistentJobQueue()
        self._running = False
        self._threads: List[threading.Thread] = []
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._register_default_handlers()

    def register_handler(self, job_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._handlers[job_type] = handler

    def _register_default_handlers(self):
        self.register_handler("vlm_inference", self._handle_vlm_inference)
        self.register_handler("highlight_render", self._handle_highlight_render)
        self.register_handler("youtube_publish", self._handle_youtube_publish)

    def start(self):
        """Starts worker pool threads."""
        self._running = True
        self._threads.clear()
        for i in range(self.max_workers):
            worker_id = f"worker_{i+1}_{uuid.uuid4().hex[:6]}"
            t = threading.Thread(target=self._worker_loop, args=(worker_id,), daemon=True, name=worker_id)
            t.start()
            self._threads.append(t)
        logger.info("Started QueueWorkerPool with %d worker threads.", self.max_workers)

    def stop(self, timeout: float = 5.0):
        """Signals worker pool to stop and waits for active jobs to finish or timeout."""
        self._running = False
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=timeout)
        self._threads.clear()
        logger.info("Stopped QueueWorkerPool.")

    def _worker_loop(self, worker_id: str):
        while self._running:
            job = self.queue.acquire_next(worker_id)
            if not job:
                time.sleep(1.0)
                continue

            job_id = job["id"]
            job_type = job["job_type"]
            payload = job["payload"]
            logger.info("[%s] Acquired job %d (%s)", worker_id, job_id, job_type)

            handler = self._handlers.get(job_type)
            if not handler:
                err_msg = f"No handler registered for job type '{job_type}'"
                logger.error(err_msg)
                self.queue.fail(job_id, err_msg)
                continue

            try:
                result = handler(payload)
                self.queue.complete(job_id, result)
                logger.info("[%s] Completed job %d (%s)", worker_id, job_id, job_type)
            except Exception as e:
                err_msg = f"Job {job_id} failed with error: {e}"
                logger.error(err_msg)
                self.queue.fail(job_id, err_msg)

    def _handle_vlm_inference(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes Stage 2 VLM inference on candidate keyframes."""
        from modules.semantic_analyzer import semantic_analyzer

        candidate_path = Path(payload["candidate_path"])
        if not candidate_path.exists():
            raise FileNotFoundError(f"Candidate video not found at {candidate_path}")

        # Execute selective keyframe VLM analysis
        analysis = semantic_analyzer.analyze_keyframe_semantics(
            video_path=candidate_path,
            start_time=0.0,
            end_time=float(payload.get("duration", 12.0)),
        )

        return {
            "candidate_id": payload.get("candidate_id"),
            "stunt_score": analysis.stunt_score,
            "humor_score": analysis.humor_score,
            "cinematic_score": analysis.cinematic_score,
            "composite_semantic_score": analysis.composite_semantic_score,
            "event_summary": analysis.event_summary,
            "suggested_hook": analysis.suggested_hook,
            "is_fallback": analysis.is_fallback,
            "semantic_status": analysis.semantic_status,
        }

    def _handle_highlight_render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Renders 1080x1920 vertical Short asynchronously."""
        from modules.pipeline import pipeline

        clip_id = payload["clip_id"]
        template = payload.get("template", "cinematic_hype")
        lang = payload.get("language", "hinglish")

        rendered_path = pipeline.render_clip_to_short(
            clip_id=clip_id,
            template_name=template,
            language=lang,
        )
        return {"clip_id": clip_id, "rendered_path": str(rendered_path)}

    def _handle_youtube_publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes clip to YouTube using fail-closed Two-Key gate."""
        from modules.youtube_uploader import youtube_uploader

        clip_id = payload["clip_id"]
        clip = db.get_clip_by_id(clip_id)
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")

        res = youtube_uploader.upload_short(
            clip_id=clip_id,
            video_path=Path(clip["final_path"]),
            title=payload.get("title", "GTA 6 Highlight #Shorts"),
            description=payload.get("description", "GTA 6 gameplay"),
            tags=payload.get("tags", ["GTA 6"]),
            privacy_status=payload.get("privacy", "private"),
            simulate=payload.get("simulate", True),
        )
        return {
            "clip_id": clip_id,
            "success": res.success,
            "youtube_url": res.youtube_url,
            "error_message": res.error_message,
        }


job_queue = PersistentJobQueue()
worker_pool = QueueWorkerPool(max_workers=config.resources.max_concurrent_workers)
