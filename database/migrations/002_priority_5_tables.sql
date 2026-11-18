-- Migration 002: Priority 5 Multi-Stream Discovery, Bounded Monitoring, Safety & Queue Architecture

-- 1. Discovered Streams (Public Metadata Only)
CREATE TABLE IF NOT EXISTS discovered_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_video_id TEXT NOT NULL UNIQUE,
    channel_id TEXT NOT NULL,
    channel_title TEXT NOT NULL,
    title TEXT NOT NULL,
    thumbnail_url TEXT,
    viewer_count INTEGER,                    -- NULL if hidden, private, or pre-live
    stream_start_time TIMESTAMP,
    ended_at TIMESTAMP,                      -- Timestamp stream concluded
    is_live INTEGER DEFAULT 1,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_polled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    has_authorized_source INTEGER DEFAULT 0  -- 0 = Metadata Only; 1 = Authorized
);

-- Backward-compatibility view
CREATE VIEW IF NOT EXISTS livestreams AS 
SELECT id, stream_video_id, channel_id, channel_title, title, viewer_count, is_live, has_authorized_source, discovered_at 
FROM discovered_streams;

-- 2. Authorized Footage Sources (Legal Permissions & Credential References)
CREATE TABLE IF NOT EXISTS authorized_footage_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    channel_title TEXT,
    creator_identity TEXT NOT NULL,          -- Verified legal / creator identity
    license_type TEXT NOT NULL,              -- 'CC-BY', 'Rockstar Press Kit', 'Written Creator Permission', 'User Owned'
    evidence_type TEXT NOT NULL,             -- 'CREATIVE_COMMONS_VERIFIED', 'WRITTEN_PERMISSION', 'USER_ORIGINAL_FOOTAGE'
    evidence_url_or_doc TEXT NOT NULL,       -- Verifiable URL, signed agreement reference, or contract hash
    permission_scope TEXT NOT NULL,          -- e.g. 'live_clipping,vertical_video_derivatives,youtube_shorts_distribution'
    permission_verified INTEGER DEFAULT 0,   -- 1 = Legally verified; 0 = Unverified
    commercial_reuse_allowed INTEGER DEFAULT 1,
    derivative_editing_allowed INTEGER DEFAULT 1,
    expiration_date TIMESTAMP,               -- Expiration timestamp of agreement
    verified_by TEXT,                        -- Auditor / compliance officer identifier
    adapter_type TEXT NOT NULL DEFAULT 'manual_upload', -- 'creator_feed', 'rtmp_pull', 'owned_recording', 'manual_upload'
    feed_endpoint_url TEXT,                  -- RTMP, SRT, WebRTC ingestion URI, or local hardware capture path
    stream_key_secret_ref TEXT,              -- Secret reference identifier (e.g. 'ENV:CREATOR_KEY'), NEVER plain text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Source Access Records (Immutable Ingestion Audit Trail)
CREATE TABLE IF NOT EXISTS source_access_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    session_id INTEGER,
    chunk_index INTEGER,
    bytes_transferred INTEGER DEFAULT 0,
    purpose TEXT NOT NULL,                   -- e.g. 'streaming_event_detection', 'highlight_extraction'
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES authorized_footage_sources(id) ON DELETE CASCADE
);

-- 4. Monitoring Sessions (Bounded Rolling Chunk Buffer Tracking)
CREATE TABLE IF NOT EXISTS monitoring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_id INTEGER NOT NULL,
    session_status TEXT DEFAULT 'active',    -- 'active', 'paused', 'stopped', 'error', 'abrupted'
    buffer_directory TEXT NOT NULL,
    total_chunks_captured INTEGER DEFAULT 0,
    total_highlights_detected INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stopped_at TIMESTAMP,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(stream_id) REFERENCES discovered_streams(id) ON DELETE CASCADE
);

-- 5. Stream Health Telemetry
CREATE TABLE IF NOT EXISTS stream_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    bitrate_kbps REAL,
    fps REAL,
    dropped_frames INTEGER DEFAULT 0,
    disconnect_count INTEGER DEFAULT 0,
    buffer_latency_sec REAL,
    status TEXT DEFAULT 'healthy',           -- 'healthy', 'degraded', 'reconnecting', 'offline'
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
);

-- 6. Detected Events (Stage 1 & Stage 2 Event Log per Chunk)
CREATE TABLE IF NOT EXISTS detected_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    timestamp_start REAL NOT NULL,
    timestamp_end REAL NOT NULL,
    stage1_motion_score REAL NOT NULL,
    stage1_audio_score REAL NOT NULL,
    stage1_heuristic_score REAL NOT NULL,
    passed_stage1 INTEGER NOT NULL,          -- 1 = Forwarded to Stage 2; 0 = Discarded
    stage2_semantic_score REAL,
    stunt_score REAL,
    humor_score REAL,
    cinematic_score REAL,
    event_summary TEXT,
    suggested_hook TEXT,
    is_fallback INTEGER DEFAULT 0,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
);

-- 7. Highlight Candidates (Extracted Highlights with Pinned Chunk References)
CREATE TABLE IF NOT EXISTS highlight_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    event_id INTEGER,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    composite_engagement_score REAL NOT NULL,
    pinned_chunk_indices TEXT NOT NULL,      -- JSON array e.g. '[12, 13, 14, 15]'
    candidate_video_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending_render',    -- 'pending_render', 'rendered', 'rejected', 'purged'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(event_id) REFERENCES detected_events(id) ON DELETE SET NULL
);

-- 8. Publishing Queue (Two-Key Gated Review & Dispatch Pipeline)
CREATE TABLE IF NOT EXISTS publishing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER NOT NULL,
    candidate_id INTEGER,
    target_channel_id TEXT,
    key1_human_approved INTEGER DEFAULT 0,   -- 1 = Explicit operator signoff; 0 = Pending review
    key2_policy_passed INTEGER DEFAULT 0,    -- 1 = Automated 8-rule compliance verified
    tier1_invariants_passed INTEGER DEFAULT 0, -- Non-overridable copyright/media integrity
    tier2_editorial_passed INTEGER DEFAULT 0,  -- Reviewable engagement/semantic fallback
    review_status TEXT DEFAULT 'pending_review', -- 'pending_review', 'approved', 'rejected', 'published'
    approved_by TEXT,
    approved_at TIMESTAMP,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE,
    FOREIGN KEY(candidate_id) REFERENCES highlight_candidates(id) ON DELETE SET NULL
);

-- 9. Persistent Background Processing Jobs (Task Queue & Recovery)
CREATE TABLE IF NOT EXISTS processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,                  -- 'chunk_analysis', 'highlight_render', 'vlm_inference', 'youtube_publish'
    priority INTEGER DEFAULT 10,             -- Lower number = higher priority
    status TEXT DEFAULT 'queued',            -- 'queued', 'running', 'completed', 'failed', 'cancelled'
    payload_json TEXT NOT NULL,
    result_json TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    worker_id TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. YouTube API Quota Usage Accounting (Pacific Time Midnight Reset)
CREATE TABLE IF NOT EXISTS youtube_api_quota_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,                  -- 'search.list', 'videos.list', 'videos.insert'
    units_consumed INTEGER NOT NULL,         -- 100 for search, 1 for videos.list, 1600 for upload
    caller_context TEXT NOT NULL,            -- 'background_discovery', 'manual_search', 'reconciliation', 'upload'
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quota_date_pt TEXT NOT NULL              -- Date in 'YYYY-MM-DD' under America/Los_Angeles timezone
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_discovered_streams_live ON discovered_streams(is_live, has_authorized_source);
CREATE INDEX IF NOT EXISTS idx_monitoring_sessions_status ON monitoring_sessions(session_status);
CREATE INDEX IF NOT EXISTS idx_stream_health_session ON stream_health(session_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_detected_events_session ON detected_events(session_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_highlight_candidates_status ON highlight_candidates(status, composite_engagement_score);
CREATE INDEX IF NOT EXISTS idx_publishing_queue_status ON publishing_queue(review_status, key1_human_approved);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_queue ON processing_jobs(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_youtube_quota_date ON youtube_api_quota_usage(quota_date_pt, recorded_at);
