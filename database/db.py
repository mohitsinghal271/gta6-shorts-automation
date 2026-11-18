"""
Database Access Object for GTA 6 AI YouTube Shorts Automation Agent
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
from config import config

logger = logging.getLogger("gta6_agent.db")


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or config.DATABASE_PATH)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager with WAL mode, 30-second busy timeout, and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def run_migrations(self, conn: sqlite3.Connection):
        """Runs versioned SQL migrations from database/migrations."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}

        migrations_dir = config.PROJECT_ROOT / "database" / "migrations"
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.sql"))
            for m_path in migration_files:
                parts = m_path.stem.split("_", 1)
                try:
                    v_num = int(parts[0])
                except ValueError:
                    continue
                if v_num not in applied:
                    with open(m_path, "r", encoding="utf-8") as f:
                        sql = f.read()
                    logger.info("Applying migration %03d: %s", v_num, m_path.name)
                    conn.executescript(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (v_num, m_path.name),
                    )
                    conn.commit()

    def init_db(self):
        schema_file = config.PROJECT_ROOT / "database" / "schema.sql"
        with self.get_connection() as conn:
            if schema_file.exists():
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)

            # Apply versioned migrations
            self.run_migrations(conn)

            # Automatic schema migration check for semantic analysis columns
            try:
                cur = conn.execute("PRAGMA table_info(clips)")
                cols = {row["name"] for row in cur.fetchall()}
                for cname, ctype in [
                    ("semantic_score", "REAL DEFAULT 0.0"),
                    ("humor_score", "REAL DEFAULT 0.0"),
                    ("stunt_score", "REAL DEFAULT 0.0"),
                    ("cinematic_score", "REAL DEFAULT 0.0"),
                    ("event_summary", "TEXT"),
                    ("approved_for_upload", "INTEGER DEFAULT 0"),
                    ("is_fallback", "INTEGER DEFAULT 0"),
                    ("semantic_status", "TEXT DEFAULT 'PENDING'"),
                ]:
                    if cname not in cols:
                        conn.execute(f"ALTER TABLE clips ADD COLUMN {cname} {ctype}")

                cur_s = conn.execute("PRAGMA table_info(sources)")
                s_cols = {row["name"] for row in cur_s.fetchall()}
                for scname, sctype in [
                    ("evidence_type", "TEXT"),
                    ("commercial_reuse_allowed", "INTEGER DEFAULT 0"),
                    ("evidence_url_or_doc", "TEXT"),
                    ("evidence_data", "TEXT"),
                ]:
                    if scname not in s_cols:
                        conn.execute(f"ALTER TABLE sources ADD COLUMN {scname} {sctype}")
            except Exception:
                pass
            conn.commit()


    def add_source(
        self,
        title: str,
        license_type: str,
        source_url: Optional[str] = None,
        creator_name: Optional[str] = None,
        permission_verified: bool = False,
        local_file_path: Optional[str] = None,
        notes: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> int:
        ev_type = evidence.get("evidence_type") if evidence else None
        comm_val = evidence.get("commercial_reuse_allowed") if evidence else False
        comm_reuse = 1 if (comm_val in (True, 1) or str(comm_val).strip().lower() in ("true", "1", "yes")) else 0
        ev_url = evidence.get("evidence_url_or_doc") if evidence else None
        ev_data = json.dumps(evidence) if evidence else None
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sources (title, source_url, creator_name, license_type, permission_verified, local_file_path, notes, evidence_type, commercial_reuse_allowed, evidence_url_or_doc, evidence_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    source_url,
                    creator_name,
                    license_type,
                    1 if permission_verified else 0,
                    local_file_path,
                    notes,
                    ev_type,
                    comm_reuse,
                    ev_url,
                    ev_data,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def update_source_verification(
        self,
        source_id: int,
        verified: bool,
        evidence: Optional[Dict[str, Any]] = None,
    ):
        ev_type = evidence.get("evidence_type") if evidence else None
        comm_val = evidence.get("commercial_reuse_allowed") if evidence else False
        comm_reuse = 1 if (comm_val in (True, 1) or str(comm_val).strip().lower() in ("true", "1", "yes")) else 0
        ev_url = evidence.get("evidence_url_or_doc") if evidence else None
        ev_data = json.dumps(evidence) if evidence else None
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sources 
                SET permission_verified = ?,
                    evidence_type = COALESCE(?, evidence_type),
                    commercial_reuse_allowed = ?,
                    evidence_url_or_doc = COALESCE(?, evidence_url_or_doc),
                    evidence_data = COALESCE(?, evidence_data)
                WHERE id = ?
                """,
                (1 if verified else 0, ev_type, comm_reuse, ev_url, ev_data, source_id),
            )
            conn.commit()

    def get_source_by_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
            return dict(row) if row else None

    def get_verified_sources(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sources WHERE permission_verified = 1 ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]


    def insert_gameplay(
        self,
        filename: str,
        filepath: str,
        file_size: int,
        duration: float,
        resolution_w: int,
        resolution_h: int,
        fps: float,
        checksum: str,
        source_id: Optional[int] = None,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO gameplay_files 
                (filename, filepath, file_size_bytes, duration_seconds, resolution_w, resolution_h, fps, checksum_sha256, source_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    filename,
                    filepath,
                    file_size,
                    duration,
                    resolution_w,
                    resolution_h,
                    fps,
                    checksum,
                    source_id,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_gameplay_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM gameplay_files WHERE checksum_sha256 = ?", (checksum,)
            ).fetchone()
            return dict(row) if row else None

    def get_gameplay_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM gameplay_files WHERE id = ?", (video_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_gameplay_status(self, video_id: int, status: str, error_message: Optional[str] = None):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE gameplay_files SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, video_id),
            )
            conn.commit()

    def list_gameplay_files(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM gameplay_files ORDER BY ingested_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_scenes(self, video_id: int, scenes: List[Dict[str, Any]]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            for idx, s in enumerate(scenes):
                cur.execute(
                    """
                    INSERT INTO scenes 
                    (video_id, scene_index, start_time, end_time, duration, motion_score, audio_energy, scene_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        video_id,
                        idx,
                        s["start_time"],
                        s["end_time"],
                        s["duration"],
                        s.get("motion_score", 0.0),
                        s.get("audio_energy", 0.0),
                        s.get("scene_type", "action"),
                    ),
                )
            conn.commit()

    def get_scenes(self, video_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scenes WHERE video_id = ? ORDER BY scene_index ASC", (video_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_clip(
        self,
        video_id: int,
        start_time: float,
        end_time: float,
        duration: float,
        engagement_score: float,
        visual_score: float = 0.0,
        action_score: float = 0.0,
        audio_score: float = 0.0,
        unpredictability_score: float = 0.0,
        hook_score: float = 0.0,
        ending_score: float = 0.0,
        scene_tags: Optional[List[str]] = None,
        language: str = "hinglish",
        voice_name: Optional[str] = None,
        template_name: str = "cinematic_hype",
        include_voiceover: bool = True,
        semantic_score: float = 0.0,
        humor_score: float = 0.0,
        stunt_score: float = 0.0,
        cinematic_score: float = 0.0,
        event_summary: Optional[str] = None,
        is_fallback: int = 0,
        semantic_status: str = "PENDING",
        candidate_path: Optional[str] = None,
        final_path: Optional[str] = None,
        status: str = "pending_review",
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO clips 
                (video_id, start_time, end_time, duration, engagement_score, visual_score, action_score, audio_score,
                 unpredictability_score, hook_score, ending_score, scene_tags, language, voice_name, template_name,
                 include_voiceover, semantic_score, humor_score, stunt_score, cinematic_score, event_summary,
                 is_fallback, semantic_status, candidate_path, final_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    start_time,
                    end_time,
                    duration,
                    engagement_score,
                    visual_score,
                    action_score,
                    audio_score,
                    unpredictability_score,
                    hook_score,
                    ending_score,
                    json.dumps(scene_tags or []),
                    language,
                    voice_name,
                    template_name,
                    1 if include_voiceover else 0,
                    semantic_score,
                    humor_score,
                    stunt_score,
                    cinematic_score,
                    event_summary,
                    1 if is_fallback else 0,
                    semantic_status,
                    candidate_path,
                    final_path,
                    status,
                ),
            )
            conn.commit()
            return cur.lastrowid


    def get_clip_by_id(self, clip_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["scene_tags"] = json.loads(res["scene_tags"] or "[]")
            return res

    def list_clips(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM clips WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if min_score is not None:
                query += " AND engagement_score >= ?"
                params.append(min_score)
            query += " ORDER BY engagement_score DESC, id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            clips = []
            for r in rows:
                c = dict(r)
                c["scene_tags"] = json.loads(c["scene_tags"] or "[]")
                clips.append(c)
            return clips

    def update_clip_status(
        self,
        clip_id: int,
        status: str,
        final_path: Optional[str] = None,
    ):
        with self.get_connection() as conn:
            if status == "approved":
                conn.execute(
                    "UPDATE clips SET status = ?, approved_for_upload = 1, final_path = COALESCE(?, final_path), approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, final_path, clip_id),
                )
            elif status == "published":
                conn.execute(
                    "UPDATE clips SET status = ?, approved_for_upload = 1, final_path = COALESCE(?, final_path) WHERE id = ?",
                    (status, final_path, clip_id),
                )
            else:
                conn.execute(
                    "UPDATE clips SET status = ?, final_path = COALESCE(?, final_path) WHERE id = ?",
                    (status, final_path, clip_id),
                )
            conn.commit()

    def set_clip_approval(self, clip_id: int, approved: bool = True):
        with self.get_connection() as conn:
            if approved:
                conn.execute(
                    "UPDATE clips SET status = 'approved', approved_for_upload = 1, approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (clip_id,),
                )
            else:
                conn.execute(
                    "UPDATE clips SET status = 'pending_review', approved_for_upload = 0 WHERE id = ?",
                    (clip_id,),
                )
            conn.commit()


    def insert_or_update_metadata(
        self,
        clip_id: int,
        title_recommended: str,
        titles: List[str],
        description: str,
        hashtags: List[str],
        tags: List[str],
        thumbnail_concept: str = "",
        pinned_comment: str = "",
        disclaimer: str = "",
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO metadata 
                (clip_id, title_recommended, titles_json, description, hashtags_json, tags_json, thumbnail_concept, pinned_comment, disclaimer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(clip_id) DO UPDATE SET
                    title_recommended = excluded.title_recommended,
                    titles_json = excluded.titles_json,
                    description = excluded.description,
                    hashtags_json = excluded.hashtags_json,
                    tags_json = excluded.tags_json,
                    thumbnail_concept = excluded.thumbnail_concept,
                    pinned_comment = excluded.pinned_comment,
                    disclaimer = excluded.disclaimer
                """,
                (
                    clip_id,
                    title_recommended,
                    json.dumps(titles),
                    description,
                    json.dumps(hashtags),
                    json.dumps(tags),
                    thumbnail_concept,
                    pinned_comment,
                    disclaimer,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_metadata(self, clip_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM metadata WHERE clip_id = ?", (clip_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["titles"] = json.loads(res["titles_json"] or "[]")
            res["hashtags"] = json.loads(res["hashtags_json"] or "[]")
            res["tags"] = json.loads(res["tags_json"] or "[]")
            return res

    def record_publishing(
        self,
        clip_id: int,
        youtube_video_id: Optional[str],
        youtube_url: Optional[str],
        privacy_status: str = "private",
        upload_status: str = "success",
        scheduled_time: Optional[str] = None,
        error_log: Optional[str] = None,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO publishing_history 
                (clip_id, youtube_video_id, youtube_url, privacy_status, scheduled_publish_time, upload_status, error_log)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clip_id,
                    youtube_video_id,
                    youtube_url,
                    privacy_status,
                    scheduled_time,
                    upload_status,
                    error_log,
                ),
            )
            if upload_status == "success":
                cur.execute("UPDATE clips SET status = 'published' WHERE id = ?", (clip_id,))
            conn.commit()
            return cur.lastrowid

    def get_publishing_history(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT p.*, c.candidate_path, c.final_path, m.title_recommended 
                FROM publishing_history p
                JOIN clips c ON p.clip_id = c.id
                LEFT JOIN metadata m ON c.id = m.clip_id
                ORDER BY p.published_at DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def get_dashboard_stats(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM gameplay_files")
            total_videos = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM clips")
            total_clips = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM clips WHERE status = 'pending_review'")
            pending_review = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM clips WHERE status = 'approved'")
            approved_clips = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM clips WHERE status = 'published'")
            published_clips = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM gameplay_files WHERE status = 'error'")
            failed_jobs = cur.fetchone()[0]

            return {
                "total_videos_processed": total_videos,
                "total_clips_generated": total_clips,
                "pending_review": pending_review,
                "approved_videos": approved_clips,
                "published_videos": published_clips,
                "failed_jobs": failed_jobs,
            }

    # =========================================================================
    # Priority 5: Discovered Streams
    # =========================================================================

    def upsert_discovered_stream(
        self,
        stream_video_id: str,
        channel_id: str,
        channel_title: str,
        title: str,
        thumbnail_url: Optional[str] = None,
        viewer_count: Optional[int] = None,
        stream_start_time: Optional[str] = None,
        is_live: bool = True,
        has_authorized_source: bool = False,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO discovered_streams 
                (stream_video_id, channel_id, channel_title, title, thumbnail_url, viewer_count,
                 stream_start_time, is_live, has_authorized_source, last_polled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(stream_video_id) DO UPDATE SET
                    title = excluded.title,
                    thumbnail_url = COALESCE(excluded.thumbnail_url, discovered_streams.thumbnail_url),
                    viewer_count = excluded.viewer_count,
                    stream_start_time = COALESCE(excluded.stream_start_time, discovered_streams.stream_start_time),
                    is_live = excluded.is_live,
                    has_authorized_source = excluded.has_authorized_source,
                    last_polled_at = CURRENT_TIMESTAMP
                """,
                (
                    stream_video_id,
                    channel_id,
                    channel_title,
                    title,
                    thumbnail_url,
                    viewer_count,
                    stream_start_time,
                    1 if is_live else 0,
                    1 if has_authorized_source else 0,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_discovered_stream_by_video_id(self, stream_video_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM discovered_streams WHERE stream_video_id = ?",
                (stream_video_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_active_discovered_streams(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM discovered_streams WHERE is_live = 1 ORDER BY viewer_count DESC NULLS LAST"
            ).fetchall()
            return [dict(r) for r in rows]

    def list_discovered_streams(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM discovered_streams ORDER BY is_live DESC, viewer_count DESC NULLS LAST, discovered_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_stream_offline(self, stream_video_id: str, ended_at: Optional[str] = None):
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE discovered_streams 
                SET is_live = 0, ended_at = COALESCE(?, CURRENT_TIMESTAMP), last_polled_at = CURRENT_TIMESTAMP
                WHERE stream_video_id = ?
                """,
                (ended_at, stream_video_id),
            )
            conn.commit()

    def set_stream_authorized_flag(self, stream_video_id: str, authorized: bool):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE discovered_streams SET has_authorized_source = ? WHERE stream_video_id = ?",
                (1 if authorized else 0, stream_video_id),
            )
            conn.commit()

    # =========================================================================
    # Priority 5: Authorized Footage Sources & Access Logging
    # =========================================================================

    def add_authorized_footage_source(
        self,
        creator_identity: str,
        license_type: str,
        evidence_type: str,
        evidence_url_or_doc: str,
        permission_scope: str = "live_clipping,vertical_video_derivatives,youtube_shorts_distribution",
        permission_verified: bool = False,
        commercial_reuse_allowed: bool = True,
        derivative_editing_allowed: bool = True,
        channel_id: Optional[str] = None,
        channel_title: Optional[str] = None,
        expiration_date: Optional[str] = None,
        verified_by: Optional[str] = None,
        adapter_type: str = "creator_feed",
        feed_endpoint_url: Optional[str] = None,
        stream_key_secret_ref: Optional[str] = None,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO authorized_footage_sources
                (creator_identity, license_type, evidence_type, evidence_url_or_doc, permission_scope,
                 permission_verified, commercial_reuse_allowed, derivative_editing_allowed,
                 channel_id, channel_title, expiration_date, verified_by, adapter_type,
                 feed_endpoint_url, stream_key_secret_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    creator_identity,
                    license_type,
                    evidence_type,
                    evidence_url_or_doc,
                    permission_scope,
                    1 if permission_verified else 0,
                    1 if commercial_reuse_allowed else 0,
                    1 if derivative_editing_allowed else 0,
                    channel_id,
                    channel_title,
                    expiration_date,
                    verified_by,
                    adapter_type,
                    feed_endpoint_url,
                    stream_key_secret_ref,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def get_authorized_footage_source_by_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM authorized_footage_sources 
                WHERE channel_id = ? AND permission_verified = 1
                ORDER BY id DESC LIMIT 1
                """,
                (channel_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_authorized_footage_source_by_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM authorized_footage_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_authorized_footage_sources(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM authorized_footage_sources ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def log_source_access(
        self,
        source_id: int,
        session_id: Optional[int],
        chunk_index: Optional[int],
        bytes_transferred: int,
        purpose: str = "streaming_event_detection",
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO source_access_records 
                (source_id, session_id, chunk_index, bytes_transferred, purpose)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, session_id, chunk_index, bytes_transferred, purpose),
            )
            conn.commit()
            return cur.lastrowid

    # =========================================================================
    # Priority 5: Monitoring Sessions & Health Telemetry
    # =========================================================================

    def create_monitoring_session(self, stream_id: int, buffer_directory: str) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO monitoring_sessions (stream_id, session_status, buffer_directory)
                VALUES (?, 'active', ?)
                """,
                (stream_id, buffer_directory),
            )
            conn.commit()
            return cur.lastrowid

    def get_monitoring_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM monitoring_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_active_monitoring_sessions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, d.title as stream_title, d.channel_title, d.stream_video_id
                FROM monitoring_sessions m
                JOIN discovered_streams d ON m.stream_id = d.id
                WHERE m.session_status = 'active'
                ORDER BY m.started_at DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def update_monitoring_session_status(self, session_id: int, status: str):
        with self.get_connection() as conn:
            stopped_clause = ", stopped_at = CURRENT_TIMESTAMP" if status in ("stopped", "error", "abrupted") else ""
            conn.execute(
                f"UPDATE monitoring_sessions SET session_status = ? {stopped_clause}, last_heartbeat = CURRENT_TIMESTAMP WHERE id = ?",
                (status, session_id),
            )
            conn.commit()

    def update_monitoring_session_heartbeat(self, session_id: int):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE monitoring_sessions SET last_heartbeat = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def increment_session_chunks(self, session_id: int):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE monitoring_sessions SET total_chunks_captured = total_chunks_captured + 1, last_heartbeat = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def increment_session_highlights(self, session_id: int):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE monitoring_sessions SET total_highlights_detected = total_highlights_detected + 1 WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def record_stream_health(
        self,
        session_id: int,
        bitrate_kbps: Optional[float],
        fps: Optional[float],
        dropped_frames: int = 0,
        disconnect_count: int = 0,
        buffer_latency_sec: Optional[float] = None,
        status: str = "healthy",
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO stream_health
                (session_id, bitrate_kbps, fps, dropped_frames, disconnect_count, buffer_latency_sec, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, bitrate_kbps, fps, dropped_frames, disconnect_count, buffer_latency_sec, status),
            )
            conn.commit()
            return cur.lastrowid

    # =========================================================================
    # Priority 5: Detected Events & Highlight Candidates
    # =========================================================================

    def record_detected_event(
        self,
        session_id: int,
        chunk_index: int,
        timestamp_start: float,
        timestamp_end: float,
        stage1_motion_score: float,
        stage1_audio_score: float,
        stage1_heuristic_score: float,
        passed_stage1: bool,
        stage2_semantic_score: Optional[float] = None,
        stunt_score: Optional[float] = None,
        humor_score: Optional[float] = None,
        cinematic_score: Optional[float] = None,
        event_summary: Optional[str] = None,
        suggested_hook: Optional[str] = None,
        is_fallback: bool = False,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO detected_events
                (session_id, chunk_index, timestamp_start, timestamp_end,
                 stage1_motion_score, stage1_audio_score, stage1_heuristic_score, passed_stage1,
                 stage2_semantic_score, stunt_score, humor_score, cinematic_score,
                 event_summary, suggested_hook, is_fallback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    chunk_index,
                    timestamp_start,
                    timestamp_end,
                    stage1_motion_score,
                    stage1_audio_score,
                    stage1_heuristic_score,
                    1 if passed_stage1 else 0,
                    stage2_semantic_score,
                    stunt_score,
                    humor_score,
                    cinematic_score,
                    event_summary,
                    suggested_hook,
                    1 if is_fallback else 0,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def add_highlight_candidate(
        self,
        session_id: int,
        start_time: float,
        end_time: float,
        duration: float,
        composite_engagement_score: float,
        pinned_chunk_indices: List[int],
        candidate_video_path: str,
        event_id: Optional[int] = None,
        status: str = "pending_render",
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO highlight_candidates
                (session_id, event_id, start_time, end_time, duration,
                 composite_engagement_score, pinned_chunk_indices, candidate_video_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_id,
                    start_time,
                    end_time,
                    duration,
                    composite_engagement_score,
                    json.dumps(pinned_chunk_indices),
                    candidate_video_path,
                    status,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def count_active_candidates(self) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM highlight_candidates WHERE status IN ('pending_render', 'rendering')")
            return cur.fetchone()[0]

    def update_highlight_candidate_status(self, candidate_id: int, status: str):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE highlight_candidates SET status = ? WHERE id = ?",
                (status, candidate_id),
            )
            conn.commit()

    # =========================================================================
    # Priority 5: Publishing Queue (Two-Key Gated Pipeline)
    # =========================================================================

    def enqueue_for_publishing(
        self,
        clip_id: int,
        candidate_id: Optional[int] = None,
        target_channel_id: Optional[str] = None,
        tier1_passed: bool = False,
        tier2_passed: bool = False,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO publishing_queue
                (clip_id, candidate_id, target_channel_id, tier1_invariants_passed, tier2_editorial_passed, review_status)
                VALUES (?, ?, ?, ?, ?, 'pending_review')
                """,
                (
                    clip_id,
                    candidate_id,
                    target_channel_id,
                    1 if tier1_passed else 0,
                    1 if tier2_passed else 0,
                ),
            )
            conn.commit()
            return cur.lastrowid

    def update_publishing_queue_keys(
        self,
        queue_id: int,
        key1_human_approved: bool,
        key2_policy_passed: bool,
        approved_by: Optional[str] = None,
    ):
        with self.get_connection() as conn:
            status = "approved" if (key1_human_approved and key2_policy_passed) else "pending_review"
            conn.execute(
                """
                UPDATE publishing_queue
                SET key1_human_approved = ?, key2_policy_passed = ?, review_status = ?,
                    approved_by = COALESCE(?, approved_by),
                    approved_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE approved_at END
                WHERE id = ?
                """,
                (
                    1 if key1_human_approved else 0,
                    1 if key2_policy_passed else 0,
                    status,
                    approved_by,
                    1 if key1_human_approved else 0,
                    queue_id,
                ),
            )
            conn.commit()

    # =========================================================================
    # Priority 5: Persistent Background Processing Task Queue
    # =========================================================================

    def enqueue_processing_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 10,
        max_retries: int = 3,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO processing_jobs (job_type, payload_json, priority, max_retries, status)
                VALUES (?, ?, ?, ?, 'queued')
                """,
                (job_type, json.dumps(payload), priority, max_retries),
            )
            conn.commit()
            return cur.lastrowid

    def acquire_next_processing_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, job_type, payload_json, retry_count, max_retries
                FROM processing_jobs
                WHERE status = 'queued'
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            job_id = row["id"]
            cur.execute(
                """
                UPDATE processing_jobs
                SET status = 'running', worker_id = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'queued'
                """,
                (worker_id, job_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return None
            res = dict(row)
            res["payload"] = json.loads(res["payload_json"])
            return res

    def complete_processing_job(self, job_id: int, result: Optional[Dict[str, Any]] = None):
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE processing_jobs
                SET status = 'completed', result_json = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(result or {}), job_id),
            )
            conn.commit()

    def fail_processing_job(self, job_id: int, error_message: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT retry_count, max_retries FROM processing_jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return
            retries = row["retry_count"] + 1
            max_r = row["max_retries"]
            if retries < max_r:
                conn.execute(
                    "UPDATE processing_jobs SET status = 'queued', retry_count = ?, error_message = ? WHERE id = ?",
                    (retries, error_message, job_id),
                )
            else:
                conn.execute(
                    "UPDATE processing_jobs SET status = 'failed', retry_count = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (retries, error_message, job_id),
                )
            conn.commit()

    def get_processing_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM processing_jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["payload"] = json.loads(res["payload_json"] or "{}")
            res["result"] = json.loads(res["result_json"] or "{}") if res.get("result_json") else None
            return res

    def requeue_interrupted_jobs(self) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE processing_jobs
                SET status = 'queued', retry_count = retry_count + 1,
                    error_message = 'Interrupted by application restart; re-queued.'
                WHERE status = 'running' AND retry_count < max_retries
                """
            )
            requeued = cur.rowcount
            cur.execute(
                """
                UPDATE processing_jobs
                SET status = 'failed', completed_at = CURRENT_TIMESTAMP,
                    error_message = 'Interrupted by application restart; max retries exceeded.'
                WHERE status = 'running' AND retry_count >= max_retries
                """
            )
            conn.commit()
            return requeued

    # =========================================================================
    # Priority 5: YouTube API Quota Accounting
    # =========================================================================

    def record_youtube_quota_usage(
        self,
        endpoint: str,
        units: int,
        caller_context: str,
        quota_date_pt: str,
    ) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO youtube_api_quota_usage
                (endpoint, units_consumed, caller_context, quota_date_pt)
                VALUES (?, ?, ?, ?)
                """,
                (endpoint, units, caller_context, quota_date_pt),
            )
            conn.commit()
            return cur.lastrowid

    def get_daily_quota_usage_pt(self, quota_date_pt: str) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(SUM(units_consumed), 0) FROM youtube_api_quota_usage WHERE quota_date_pt = ?",
                (quota_date_pt,),
            )
            return cur.fetchone()[0]


db = Database()
