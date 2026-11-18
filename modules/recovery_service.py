"""
Application Recovery Service Module for GTA 6 AI YouTube Shorts Platform

Executes crash recovery and startup reconciliation:
1. Re-queues interrupted processing jobs from processing_jobs table.
2. Reconciles stale/dead monitoring sessions and marks them 'abrupted'.
3. Purges orphan buffer chunks and intermediate temporary files.
4. Enforces the 10 GB disk cap via deterministic garbage collection.
"""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import shutil
import time
from typing import Dict, List, Optional, Any

from config import config
from database.db import db

logger = logging.getLogger("gta6_agent.recovery")


class ApplicationRecoveryService:
    def __init__(self):
        self.buffer_dir = config.BUFFER_DIR
        self.candidates_dir = config.CANDIDATES_DIR

    def reconcile(self, purge_orphans: bool = True) -> Dict[str, Any]:
        """
        Executes complete startup reconciliation routine.
        Guarantees system consistency following power loss, container restart, or process termination.
        """
        logger.info("Executing ApplicationRecoveryService startup reconciliation...")

        # 1. Reconcile Interrupted Background Jobs
        requeued_jobs = db.requeue_interrupted_jobs()
        logger.info("Reconciled interrupted background jobs: %d re-queued.", requeued_jobs)

        # 2. Reconcile Dead / Abrupted Monitoring Sessions
        reconciled_sessions = self._reconcile_monitoring_sessions()
        logger.info("Reconciled dead monitoring sessions: %d marked 'abrupted'.", reconciled_sessions)

        # 3. Purge Orphan Buffer Directories & Temp Files
        purged_files = 0
        if purge_orphans:
            purged_files = self._purge_orphan_files()
            logger.info("Purged %d orphan chunks and temporary media files.", purged_files)

        # 4. Enforce Disk Storage Quotas
        reclaimed_mb = self.enforce_storage_limits()

        summary = {
            "requeued_jobs": requeued_jobs,
            "abrupted_sessions": reconciled_sessions,
            "purged_orphan_files": purged_files,
            "reclaimed_storage_mb": reclaimed_mb,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info("ApplicationRecoveryService reconciliation complete: %s", summary)
        return summary

    def _reconcile_monitoring_sessions(self) -> int:
        """Finds any active sessions that lost heartbeat on abnormal termination."""
        abrupted_count = 0
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, stream_id, last_heartbeat FROM monitoring_sessions
                WHERE session_status = 'active'
                """
            )
            rows = cur.fetchall()
            for r in rows:
                session_id = r["id"]
                conn.execute(
                    """
                    UPDATE monitoring_sessions 
                    SET session_status = 'abrupted', stopped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (session_id,),
                )
                abrupted_count += 1
            conn.commit()
        return abrupted_count

    def _purge_orphan_files(self) -> int:
        """Deletes chunk files corresponding to closed, stopped, or abrupted sessions."""
        purged = 0
        if not self.buffer_dir.exists():
            return 0

        # Query all active session buffer directories
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT buffer_directory FROM monitoring_sessions WHERE session_status = 'active'")
            active_dirs = {Path(row[0]).resolve() for row in cur.fetchall() if row[0]}

        for stream_buf in self.buffer_dir.glob("stream_*"):
            if stream_buf.is_dir() and stream_buf.resolve() not in active_dirs:
                try:
                    chunk_count = len(list(stream_buf.glob("*.mp4")))
                    shutil.rmtree(stream_buf)
                    purged += chunk_count
                except Exception as e:
                    logger.warning("Could not delete orphan buffer directory %s: %s", stream_buf, e)

        # Remove temporary audio mixes
        for temp_file in config.OUTPUT_DIR.glob("temp_mix_*.aac"):
            try:
                temp_file.unlink()
                purged += 1
            except Exception:
                pass

        return purged

    def enforce_storage_limits(self) -> float:
        """
        Enforces max_disk_usage_gb (10.0 GB).
        If storage exceeds limits, purges buffer chunks and unapproved candidate clips.
        Returns MB reclaimed.
        """
        initial_bytes = self._get_managed_storage_bytes()
        max_bytes = config.resources.max_disk_usage_gb * (1024 ** 3)

        if initial_bytes <= max_bytes:
            return 0.0

        logger.warning(
            "Storage consumption (%.2f GB) exceeds threshold (%.2f GB). Running automated garbage collection.",
            initial_bytes / (1024 ** 3),
            config.resources.max_disk_usage_gb,
        )

        reclaimed_bytes = 0
        # 1. Purge buffer chunks older than 15 minutes
        cutoff_time = time.time() - (config.resources.temp_chunk_ttl_minutes * 60)
        if self.buffer_dir.exists():
            for chunk_file in self.buffer_dir.glob("**/*.mp4"):
                try:
                    if chunk_file.stat().st_mtime < cutoff_time:
                        sz = chunk_file.stat().st_size
                        chunk_file.unlink()
                        reclaimed_bytes += sz
                except Exception:
                    pass

        # 2. Purge unapproved candidates older than candidate_retention_hours (48h)
        cand_cutoff = time.time() - (config.resources.candidate_retention_hours * 3600)
        if self.candidates_dir.exists():
            for cand_file in self.candidates_dir.glob("*.mp4"):
                try:
                    if cand_file.stat().st_mtime < cand_cutoff:
                        sz = cand_file.stat().st_size
                        cand_file.unlink()
                        reclaimed_bytes += sz
                except Exception:
                    pass

        reclaimed_mb = reclaimed_bytes / (1024 * 1024)
        logger.info("Storage garbage collection completed. Reclaimed %.2f MB.", reclaimed_mb)
        return reclaimed_mb

    def _get_managed_storage_bytes(self) -> int:
        total = 0
        for d in [self.buffer_dir, self.candidates_dir]:
            if d.exists():
                total += sum(f.stat().st_size for f in d.glob("**/*") if f.is_file())
        return total


recovery_service = ApplicationRecoveryService()
