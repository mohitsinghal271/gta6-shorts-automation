"""
24/7 Background Daemon Service for GTA 6 AI YouTube Shorts Platform

Orchestrates all autonomous 24/7 operations:
1. Persistent task worker pool (video rendering, VLM analysis, publishing).
2. Periodic livestream discovery (every 30 minutes, Pacific Time quota tracking).
3. Periodic disk garbage collection and recovery reconciliation (every 2 hours).
4. Auto-publishing of approved clips to YouTube (@gta-6-rampage).
5. Graceful shutdown on SIGTERM/SIGINT.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
import threading

from config import config
from database.db import db
from modules.job_queue import QueueWorkerPool
from modules.livestream_discovery import LivestreamDiscoveryService
from modules.recovery_service import ApplicationRecoveryService
from modules.youtube_uploader import youtube_uploader

# Setup root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOGS_DIR / "daemon_service.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("gta6_agent.daemon")


class GTA6AutonomousDaemon:
    def __init__(
        self,
        worker_concurrency: int = 2,
        discovery_interval_seconds: int = 1800,  # 30 mins
        maintenance_interval_seconds: int = 7200,  # 2 hours
        auto_publish_interval_seconds: int = 600,  # 10 mins
    ):
        self.worker_concurrency = worker_concurrency
        self.discovery_interval = discovery_interval_seconds
        self.maintenance_interval = maintenance_interval_seconds
        self.auto_publish_interval = auto_publish_interval_seconds

        self.running = False
        self.worker_pool = QueueWorkerPool(max_workers=self.worker_concurrency)
        self.discovery_service = LivestreamDiscoveryService()
        self.recovery_service = ApplicationRecoveryService()

    def start(self):
        self.running = True
        logger.info("=====================================================")
        logger.info("   GTA 6 AI Shorts Automation — 24/7 Cloud Daemon    ")
        logger.info("   Channel: @gta-6-rampage | Workers: %d            ", self.worker_concurrency)
        logger.info("=====================================================")

        # 1. Startup Recovery Reconciliation
        logger.info("[Startup] Running initial recovery & storage reconciliation...")
        rec_summary = self.recovery_service.reconcile(purge_orphans=True)
        logger.info("[Startup] Recovery complete: %s", rec_summary)

        # 2. Start Background Worker Pool
        logger.info("[WorkerPool] Starting %d background worker threads...", self.worker_concurrency)
        self.worker_pool.start()

        # 3. Spawn Periodic Discovery Thread
        t_disc = threading.Thread(target=self._discovery_loop, daemon=True, name="DiscoveryLoop")
        t_disc.start()

        # 4. Spawn Maintenance & Recovery Thread
        t_maint = threading.Thread(target=self._maintenance_loop, daemon=True, name="MaintenanceLoop")
        t_maint.start()

        # 5. Spawn Auto-Publish Thread
        t_pub = threading.Thread(target=self._publishing_loop, daemon=True, name="PublishingLoop")
        t_pub.start()

        logger.info("GTA 6 Automation Daemon is actively running 24/7.")
        while self.running:
            time.sleep(1.0)

    def stop(self):
        if not self.running:
            return
        logger.info("Initiating graceful shutdown of GTA 6 Daemon...")
        self.running = False
        self.worker_pool.stop(timeout=10.0)
        logger.info("Daemon service stopped safely.")

    def _discovery_loop(self):
        """Periodically polls for active GTA 6 streams."""
        logger.info("[DiscoveryLoop] Started. Polling cadence: every %ds.", self.discovery_interval)
        while self.running:
            try:
                logger.info("[DiscoveryLoop] Executing scheduled livestream discovery...")
                streams = self.discovery_service.discover_active_streams(
                    query="GTA 6",
                    max_results=10,
                    is_manual=False,
                    force_refresh=True,
                )
                logger.info("[DiscoveryLoop] Discovered %d active streams.", len(streams))
            except Exception as e:
                logger.error("[DiscoveryLoop] Error during discovery: %s", e)

            # Sleep in small increments for fast shutdown response
            for _ in range(self.discovery_interval):
                if not self.running:
                    break
                time.sleep(1.0)

    def _maintenance_loop(self):
        """Periodically runs garbage collection to ensure disk cap <= 10GB."""
        logger.info("[MaintenanceLoop] Started. Running every %ds.", self.maintenance_interval)
        while self.running:
            for _ in range(self.maintenance_interval):
                if not self.running:
                    break
                time.sleep(1.0)

            if not self.running:
                break

            try:
                logger.info("[MaintenanceLoop] Running scheduled storage & session reconciliation...")
                summary = self.recovery_service.reconcile(purge_orphans=True)
                logger.info("[MaintenanceLoop] Maintenance complete: %s", summary)
            except Exception as e:
                logger.error("[MaintenanceLoop] Maintenance error: %s", e)

    def _publishing_loop(self):
        """Periodically checks publishing queue and uploads approved clips."""
        logger.info("[PublishingLoop] Started. Checking approved queue every %ds.", self.auto_publish_interval)
        while self.running:
            for _ in range(self.auto_publish_interval):
                if not self.running:
                    break
                time.sleep(1.0)

            if not self.running:
                break

            try:
                # Find approved clips not yet published
                approved_clips = db.list_clips(status="approved", limit=5)
                for clip in approved_clips:
                    clip_id = clip["id"]
                    final_path = clip.get("final_path") or clip.get("candidate_path")
                    if not final_path or not Path(final_path).exists():
                        continue

                    meta = db.get_metadata(clip_id)
                    title = meta["title_recommended"] if meta else "GTA 6 Rampage Viral Moment"
                    desc = meta["description"] if meta else "#GTA6 #Shorts"
                    tags = meta.get("tags", ["GTA 6"]) if meta else ["GTA 6"]

                    logger.info("[PublishingLoop] Enqueueing upload for approved clip %d: '%s'", clip_id, title)
                    self.worker_pool.queue.enqueue(
                        job_type="youtube_publish",
                        payload={
                            "clip_id": clip_id,
                            "video_path": str(final_path),
                            "title": title,
                            "description": desc,
                            "tags": tags,
                            "privacy_status": config.youtube.default_privacy,
                            "simulate": config.youtube.simulate_upload,
                        },
                        priority=20,
                    )
            except Exception as e:
                logger.error("[PublishingLoop] Error checking approved clips: %s", e)


def main():
    daemon = GTA6AutonomousDaemon()

    def _sig_handler(signum, frame):
        logger.info("Signal %d received, stopping daemon...", signum)
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
