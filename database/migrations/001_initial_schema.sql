-- Migration 001: Initial Schema (Priority 1-4 Baseline)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_url TEXT,
    creator_name TEXT,
    license_type TEXT NOT NULL,
    permission_verified INTEGER DEFAULT 0,
    local_file_path TEXT,
    notes TEXT,
    evidence_type TEXT,
    commercial_reuse_allowed INTEGER DEFAULT 0,
    evidence_url_or_doc TEXT,
    evidence_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gameplay_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    file_size_bytes INTEGER,
    duration_seconds REAL,
    resolution_w INTEGER,
    resolution_h INTEGER,
    fps REAL,
    checksum_sha256 TEXT UNIQUE,
    source_id INTEGER,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    scene_index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    motion_score REAL DEFAULT 0.0,
    audio_energy REAL DEFAULT 0.0,
    scene_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES gameplay_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration REAL NOT NULL,
    engagement_score REAL DEFAULT 0.0,
    visual_score REAL DEFAULT 0.0,
    action_score REAL DEFAULT 0.0,
    audio_score REAL DEFAULT 0.0,
    unpredictability_score REAL DEFAULT 0.0,
    hook_score REAL DEFAULT 0.0,
    ending_score REAL DEFAULT 0.0,
    scene_tags TEXT,
    language TEXT DEFAULT 'hinglish',
    voice_name TEXT,
    template_name TEXT DEFAULT 'cinematic_hype',
    include_voiceover INTEGER DEFAULT 1,
    semantic_score REAL DEFAULT 0.0,
    humor_score REAL DEFAULT 0.0,
    stunt_score REAL DEFAULT 0.0,
    cinematic_score REAL DEFAULT 0.0,
    event_summary TEXT,
    is_fallback INTEGER DEFAULT 0,
    semantic_status TEXT DEFAULT 'PENDING',
    approved_for_upload INTEGER DEFAULT 0,
    candidate_path TEXT,
    final_path TEXT,
    status TEXT DEFAULT 'pending_review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    FOREIGN KEY(video_id) REFERENCES gameplay_files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER NOT NULL UNIQUE,
    title_recommended TEXT NOT NULL,
    titles_json TEXT NOT NULL,
    description TEXT NOT NULL,
    hashtags_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    thumbnail_concept TEXT,
    pinned_comment TEXT,
    disclaimer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS publishing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER NOT NULL,
    youtube_video_id TEXT,
    youtube_url TEXT,
    privacy_status TEXT DEFAULT 'private',
    scheduled_publish_time TEXT,
    published_at TIMESTAMP,
    upload_status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE
);
