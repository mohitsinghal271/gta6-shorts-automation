# Priority 5 Architecture Specification & Implementation Plan
## Automated GTA 6 Livestream Discovery, Bounded Monitoring, Highlight Extraction, and Fail-Closed Publishing Platform

- **Project**: GTA_6 Video Automation Platform (Priority 5 Evolution)
- **Author**: Core Systems Architecture & Forensic QA Team
- **Date**: 2026-11-13
- **Version**: 1.1.0 (Phase 1 Deliverable — Pre-Implementation Architectural Blueprint with 10 Engineering Corrections)
- **Status**: PENDING_USER_APPROVAL (Execution strictly halts upon completion of Phase 1; zero existing source code modified)
- **Target Working Directory**: `C:\Users\idea\OneDrive\Desktop\projects\GTA_6`
- **Integrity Mode**: Strict Development & Audit Mode (Authentic Logic, No Facades, No Hardcoded Shortcuts)

---

## Table of Contents

1. [Executive Summary & Repository Audit](#1-executive-summary--repository-audit)
   - [1.1 Mission & Architectural Scope](#11-mission--architectural-scope)
   - [1.2 Comprehensive Audit of the 15 Existing Application Modules](#12-comprehensive-audit-of-the-15-existing-application-modules)
   - [1.3 Database Architecture & Schema Audit](#13-database-architecture--schema-audit)
   - [1.4 CLI Command Architecture Audit](#14-cli-command-architecture-audit)
   - [1.5 Web Application & Dashboard Architecture Audit](#15-web-application--dashboard-architecture-audit)
   - [1.6 YouTube OAuth 2.0 Integration & Credential Audit](#16-youtube-oauth-20-integration--credential-audit)
   - [1.7 1080p 60FPS Benchmark & Sample Footage Audit](#17-1080p-60fps-benchmark--sample-footage-audit)
   - [1.8 Existing Test Suite Baseline](#18-existing-test-suite-baseline)
2. [Existing vs. Missing Functionality Gap Analysis](#2-existing-vs-missing-functionality-gap-analysis)
   - [2.1 Comprehensive Capability Matrix](#21-comprehensive-capability-matrix)
   - [2.2 Anti-Duplication Directives (What to Preserve vs. What to Build)](#22-anti-duplication-directives-what-to-preserve-vs-what-to-build)
3. [Multi-Stream Discovery Architecture](#3-multi-stream-discovery-architecture)
   - [3.1 YouTube Data API v3 Two-Step Search & Viewer Count Specification](#31-youtube-data-api-v3-two-step-search--viewer-count-specification)
   - [3.2 Quota Economics, Intelligent Polling & Request Accounting](#32-quota-economics-intelligent-polling--request-accounting)
   - [3.3 Stream Discovery Data Contract, Caching & Stale Stream Lifecycle Reconciliation](#33-stream-discovery-data-contract-caching--stale-stream-lifecycle-reconciliation)
   - [3.4 Discovery-Only Isolation Guarantee](#34-discovery-only-isolation-guarantee)
4. [Footage Acquisition Separation & Legal Compliance](#4-footage-acquisition-separation--legal-compliance)
   - [4.1 Architectural Decoupling: Discovery vs. Acquisition](#41-architectural-decoupling-discovery-vs-acquisition)
   - [4.2 The AuthorizedSourceAdapter Interface Specification](#42-the-authorizedsourceadapter-interface-specification)
   - [4.3 Concrete Acquisition Adapters, Credential Hardening & Candidate Admission Throttling](#43-concrete-acquisition-adapters-credential-hardening--candidate-admission-throttling)
   - [4.4 Legal Evidence Verification, Access Logging & Dashboard Gating](#44-legal-evidence-verification-access-logging--dashboard-gating)
5. [Concurrent Stream Processing & Bounded Resource Policies](#5-concurrent-stream-processing--bounded-resource-policies)
   - [5.1 Bounded Rolling Chunk Ring Buffer Architecture & Context Pinning (10–15s Chunks)](#51-bounded-rolling-chunk-ring-buffer-architecture--context-pinning-1015s-chunks)
   - [5.2 Hard Resource Caps, Concurrency Limits & Asynchronous Decoupling](#52-hard-resource-caps-concurrency-limits--asynchronous-decoupling)
   - [5.3 CPU Thread Governance & Optional GPU Hardware Acceleration](#53-cpu-thread-governance--optional-gpu-hardware-acceleration)
   - [5.4 Storage Thresholds, Candidate Admission Throttling & Deterministic Garbage Collection](#54-storage-thresholds-candidate-admission-throttling--deterministic-garbage-collection)
6. [Low-Latency Two-Stage Event Detection](#6-low-latency-two-stage-event-detection)
   - [6.1 High-Throughput Streaming Event Pipeline Overview](#61-high-throughput-streaming-event-pipeline-overview)
   - [6.2 Stage 1: Fast Heuristic CV & Audio Filtering (1–2s per Chunk)](#62-stage-1-fast-heuristic-cv--audio-filtering-12s-per-chunk)
   - [6.3 Stage 2: Selective Semantic AI Gameplay Analysis (Keyframe VLM) & Fallback Semantics](#63-stage-2-selective-semantic-ai-gameplay-analysis-keyframe-vlm--fallback-semantics)
   - [6.4 Temporal IoU Non-Maximum Suppression (NMS) & Highlight Ranking](#64-temporal-iou-non-maximum-suppression-nms--highlight-ranking)
7. [Conditional Frame Rate Handling](#7-conditional-frame-rate-handling)
   - [7.1 The Frame Rate Preservation Principle](#71-the-frame-rate-preservation-principle)
   - [7.2 Source Frame Rate Probing & Target Calculation](#72-source-frame-rate-probing--target-calculation)
   - [7.3 Filtergraph Modifications & Elimination of Hardcoded 30 FPS](#73-filtergraph-modifications--elimination-of-hardcoded-30-fps)
8. [Fail-Closed Publishing Safety & Security Hardening](#8-fail-closed-publishing-safety--security-hardening)
   - [8.1 Forensic Analysis of the Critical Bypass Vulnerability](#81-forensic-analysis-of-the-critical-bypass-vulnerability)
   - [8.2 The Fail-Closed Two-Key Gate Architecture & Rule Hierarchy](#82-the-fail-closed-two-key-gate-architecture--rule-hierarchy)
   - [8.3 Decoupling Approval from Upload & Real-Time Re-Evaluation](#83-decoupling-approval-from-upload--real-time-re-evaluation)
   - [8.4 Tri-Simulation Settings & Fail-Gracefully Guarantees](#84-tri-simulation-settings--fail-gracefully-guarantees)
   - [8.5 Credential Secrecy, .gitignore Hardening & Zero-Sibling-Traversal Guarantee](#85-credential-secrecy-gitignore-hardening--zero-sibling-traversal-guarantee)
9. [Database Migrations & Schema Extensions](#9-database-migrations--schema-extensions)
   - [9.1 SQLite Engine Hardening: WAL Mode & Concurrency Configuration](#91-sqlite-engine-hardening-wal-mode--concurrency-configuration)
   - [9.2 Versioned Migration Runner Architecture](#92-versioned-migration-runner-architecture)
   - [9.3 Comprehensive Database Schema Architecture: Existing vs. New Tables (R1–R12)](#93-comprehensive-database-schema-architecture-existing-vs-new-tables-r1r12)
10. [Application Restart Recovery & Persistence](#10-application-restart-recovery--persistence)
    - [10.1 Persistent SQLite Task Queue Architecture](#101-persistent-sqlite-task-queue-architecture)
    - [10.2 The ApplicationRecoveryService Startup Reconciler](#102-the-applicationrecoveryservice-startup-reconciler)
    - [10.3 Crash Recovery State Machine](#103-crash-recovery-state-machine)
11. [Dashboard & CLI Enhancements](#11-dashboard--cli-enhancements)
    - [11.1 Web Application Architecture Upgrades (`web_app.py`)](#111-web-application-architecture-upgrades-web_apppy)
    - [11.2 Streamlit Dashboard Upgrades (`app.py`)](#112-streamlit-dashboard-upgrades-apppy)
    - [11.3 CLI Command Extensions (`cli.py`)](#113-cli-command-extensions-clipy)
12. [Comprehensive 25-Point Automated Test Suite Plan](#12-comprehensive-25-point-automated-test-suite-plan)
    - [12.1 Test Suite Organization & Mocking Strategy](#121-test-suite-organization--mocking-strategy)
    - [12.2 Detailed Specifications for Test Cases 1 through 25](#122-detailed-specifications-for-test-cases-1-through-25)
13. [Risks, Tradeoffs & Mitigations](#13-risks-tradeoffs--mitigations)
    - [13.1 Technical Risk Matrix](#131-technical-risk-matrix)
    - [13.2 Legal, Policy & Operational Safeguards](#132-legal-policy--operational-safeguards)
14. [Roadmap for Subsequent Phases (R2–R12)](#14-roadmap-for-subsequent-phases-r2r12)
    - [14.1 Execution Phases & Dependency Graph](#141-execution-phases--dependency-graph)
    - [14.2 Detailed Milestone Deliverables (M2 through M10)](#142-detailed-milestone-deliverables-m2-through-m10)
    - [14.3 Explicit User Approval Halting Protocol](#143-explicit-user-approval-halting-protocol)

---

## 1. Executive Summary & Repository Audit

### 1.1 Mission & Architectural Scope
The GTA 6 video automation platform currently operates as a high-fidelity, single-video batch processing pipeline. Given an ingested video file (e.g., an MP4 recording in `input/`), the system executes visual scene cut detection, sliding-window motion/audio heuristics, selective keyframe extraction, Vision-Language Model (VLM) evaluation, composite highlight ranking, FFmpeg sub-clip extraction, ASS dynamic karaoke subtitle generation, AI commentary synthesis (Edge-TTS / SAPI), audio ducking, vertical 9:16 blurred-stack composition, 8-rule compliance validation, and YouTube OAuth 2.0 uploading.

**The Priority 5 Evolution** expands this foundation into a production-grade, 24/7 automated platform capable of:
1. **Discovering** public live GTA 6 streams via the YouTube Data API v3 while strictly isolating discovery metadata from video footage access.
2. **Ingesting** short rolling chunks (10–15 seconds) from permitted, authorized feeds without accumulating unbounded 5–24 hour archive files.
3. **Evaluating** gameplay events in near-real-time using low-latency two-stage filtering (fast CV/audio motion deltas $\to$ selective 3-keyframe VLM inference).
4. **Generating** 1080x1920 vertical YouTube Shorts that conditionally preserve high-framerate 60 FPS gameplay when present or natively render 30/25 FPS footage without artificial frame duplication.
5. **Enforcing** an uncompromising, fail-closed publishing safety architecture where missing source rights or corrupted media can never be bypassed by human approval.
6. **Surviving** process terminations through SQLite Write-Ahead Logging (WAL), persistent background task queues, and automated startup state reconciliation.

---

### 1.2 Comprehensive Audit of the 15 Existing Application Modules

Direct static analysis of `C:\Users\idea\OneDrive\Desktop\projects\GTA_6\modules` reveals an exceptionally clean, decoupled Python architecture comprising 15 specialized modules:

| Module | Lines of Code | Core Responsibilities & Internal Mechanisms | Critical Findings & Evolution Needs |
|---|---|---|---|
| **`audio_processor.py`** | 140 | Audio stream probing via FFmpeg; multi-track mixing; dynamic gameplay audio ducking via `sidechaincompress=threshold=0.08:ratio=5:attack=20:release=300`. | **Gaps**: Parameter `bgm_audio` is in signature (line 34) but omitted from filtergraph; EBU R128 loudness (`-af loudnorm`) is promised in docstrings but absent from FFmpeg filters. |
| **`clip_generator.py`** | 165 | Frame-accurate sub-clip extraction from source video using `-ss`, `-t`, `-c:v libx264`, `-crf 18`, `-preset fast`, and `-avoid_negative_ts make_zero`. | **Strengths**: Re-encodes candidate clips so intermediate cuts start with clean I-frames at timestamp 0.0s. **Evolution**: Must adapt to accept in-memory/chunked buffers rather than full files. |
| **`duplicate_detector.py`** | 49 | File deduplication via SHA256 checksums; temporal segment overlap checking via 1D temporal IoU; upload history checks. | **Strengths**: Lightweight and effective. Will be integrated into stream chunk candidate ranking. |
| **`gameplay_ingestion.py`** | 135 | File inspection via ffprobe/ffmpeg; extracts width, height, duration, and FPS; registers records in `gameplay_files`. | **Limitation**: Tightly coupled to static on-disk files. Needs abstraction to support rolling stream chunks. |
| **`highlight_ranker.py`** | 155 | Combines motion, audio, semantic, hook, and ending scores into composite engagement score; applies 1D temporal Non-Maximum Suppression (NMS) with `max_overlap_iou=0.30`. | **Strengths**: Highly reusable. When semantic analysis is in fallback mode, it automatically drops the semantic weight and recalculates CV/audio composite. |
| **`metadata_generator.py`** | 180 | Generates 3 candidate titles, recommended title, SEO description, hashtags, tags, thumbnail concept, and Rockstar Games copyright disclaimer. | **Strengths**: Incorporates detected event summaries (e.g., "POLICE CHASE") into title templates. |
| **`pipeline.py`** | 275 | `PipelineOrchestrator` coordinating the 11-step batch workflow. Manages pre-ranking shortlist (top 15) to throttle VLM calls. | **Limitation**: 100% synchronous batch execution. Must be refactored to support asynchronous job queues. |
| **`publishing_policy.py`** | 290 | Automated 8-rule compliance gate: engagement threshold ($\ge 85$), source rights verified, semantic not fallback, physical media spec (1080x1920, 15-60s, audio present), duplicate check, metadata presence. | **Strengths**: High-integrity validator. **Flaw**: Its evaluation was being bypassed in `youtube_uploader.py`. |
| **`scene_detector.py`** | 125 | Streams video at 4 FPS downscaled to 160x90 via FFmpeg rawvideo pipe; computes grayscale pixel delta between consecutive frames; detects cuts at `threshold=28.0`. | **Strengths**: Extremely fast and lightweight. Serves as the direct foundation for Stage 1 streaming motion detection. |
| **`semantic_analyzer.py`** | 385 | Keyframe extractor (Hook, Action Peak, Climax); transmits base64 frames to local Ollama VLM (`moondream`/`qwen_vision`); structured JSON scoring; neutral fallback scoring (54.25). | **Strengths**: Factual fallback prevents hallucinations when offline. Monotonic keyframe extraction prevents timestamp inversions. |
| **`source_discovery.py`** | 270 | Mode B source registration; manages license categories (`CC-BY`, `Rockstar Press Kit Official`, `Authorized Creator Submission`); validates permission evidence URLs/docs. | **Limitation**: Currently only registers local files. Does not interact with YouTube Data API. |
| **`subtitle_generator.py`** | 170 | Generates SRT and ASS dynamic karaoke subtitles with yellow highlight `{\c&H0000FFFF&\b1}` on active spoken words; positioned at `MarginV: 480` to avoid YouTube Shorts UI overlays. | **Strengths**: High-quality karaoke typography with full Devanagari UTF-8 support. |
| **`video_analyzer.py`** | 220 | Sweeps sliding windows (35s duration, 5s step); computes audio RMS energy in 0.5s intervals; computes action/unpredictability/hook/ending metrics. | **Limitation**: Batch-oriented. Must be adapted into a streaming chunk evaluator for 10–15s windows. |
| **`video_editor.py`** | 225 | Renders 1080x1920 vertical video using blurred background stack or intelligent center crop; burns ASS subtitles; applies color grading and vignettes. | **Bugs**: Hardcoded `:fps=30` in `zoompan` filter; `-threads 0` consumes all CPU cores indiscriminately. |
| **`voice_generator.py`** | 450 | Commentary synthesis in Hindi, English, and Hinglish; dynamic script generation via Qwen; synthesis via Microsoft Edge-TTS with fallback to Windows SAPI. | **Strengths**: Extracts `WordBoundary` timestamps from Edge-TTS to drive word-accurate ASS karaoke subtitles. |
| **`youtube_uploader.py`** | 270 | Resumable chunked upload via Google API Client; OAuth 2.0 flow; simulation mode generating `sim_{clip_id}_{timestamp}` mock records. | **CRITICAL FLAW**: Lines 164–184 skip `publishing_policy.evaluate()` if `is_approved == True`, allowing human approval to bypass copyright and safety checks. |

---

### 1.3 Database Architecture & Schema Audit
The database layer (`database/db.py`) uses Python’s built-in `sqlite3` without an external ORM. It manages the active database file `database/gta6_shorts.db`.

#### Base Schema (`database/schema.sql`):
1. **`sources`**: Tracks source titles, URLs, creator identities, license types, and verified permission flags.
2. **`gameplay_files`**: Tracks ingested files, filepaths, resolutions, durations, frame rates, SHA256 checksums, and source FKs.
3. **`scenes`**: Scene boundaries identified by cut detection with motion scores and audio energy metrics.
4. **`clips`**: Extracted candidate and final clips with individual metric scores, semantic evaluations, fallback flags, and approval statuses.
5. **`metadata`**: Recommended and candidate titles, descriptions, hashtags, tags, thumbnail concepts, and disclaimers.
6. **`publishing_history`**: YouTube upload records, video IDs, URLs, privacy statuses, and error logs.

#### Architectural Deficiencies Identified in DB Layer:
- **No WAL Mode**: `db.py:21-30` opens a new connection per query with default journal mode (rollback journal). Under concurrent background processing or multi-stream monitoring, SQLite locks the entire database file during writes, raising `sqlite3.OperationalError: database is locked`.
- **Missing Busy Timeout**: Connections are created without a `timeout` argument (defaulting to 5.0 seconds).
- **Ad-hoc Dynamic Migrations**: `db.py:42-70` checks `PRAGMA table_info` and issues `ALTER TABLE ADD COLUMN` inside a bare `try...except Exception: pass` block. There is no `schema_migrations` tracking table, no migration versioning, and failures are silently suppressed.

---

### 1.4 CLI Command Architecture Audit
`cli.py` defines 9 commands via `argparse`:
- `scan`: Scans `input/` directory for uningested gameplay files.
- `ingest <filepath>`: Ingests and probes a single video file into SQLite.
- `analyze <video_id> [--top 5]`: Runs scene cut detection, sliding window analysis, and candidate ranking.
- `list-clips [--status] [--limit 20]`: Lists generated clips, engagement scores, and file paths.
- `approve <clip_id>`: Marks a clip as approved for upload.
- `upload <clip_id> [--privacy] [--simulate]`: Publishes a clip to YouTube or simulates upload.
- `run-pipeline <filepath> [--lang] [--template] [--top 3] [--no-voice]`: Executes the complete 11-step pipeline.
- `stats`: Displays database aggregate metrics.
- `channel-status`: Probes YouTube OAuth channel connectivity.

**Missing CLI Functionality**:
- No commands to search or discover YouTube livestreams (`discover-streams`).
- No commands to start, stop, or inspect livestream monitoring sessions (`monitor`).
- No background queue worker execution command (`worker`).
- No database migration or recovery command (`migrate`, `recover`).

---

### 1.5 Web Application & Dashboard Architecture Audit
The repository contains two user interface implementations:
1. **FastAPI Application (`web_app.py`)**: Runs on port 8501. Serves inline Tailwind CSS HTML with KPI cards, video upload form, and clip review queue with video players.
   - **Severe Flaw**: Endpoint `POST /api/upload` invokes `pipeline.process_video_pipeline()` **synchronously** inside the HTTP request handler. An upload freezes the HTTP server for 60–120 seconds.
2. **Streamlit Application (`app.py`)**: Provides interactive widgets for parameter selection, clip review, and publishing history. Runs pipeline synchronously in the Streamlit execution thread.

**Missing Dashboard Capabilities**:
- Zero interface elements for discovering, filtering, or viewing live YouTube streams.
- No monitoring session controls (Start/Stop stream monitoring, buffer latency, health metrics).
- No background task queue status or worker activity monitor.
- No visual differentiation between public discovery metadata and legally authorized video feeds.

---

### 1.6 YouTube OAuth 2.0 Integration & Credential Audit
- **Scopes**: `youtube_uploader.py:28` specifies `SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]`.
  - *Finding*: This scope strictly permits video uploading. It **cannot** perform YouTube Data API stream searches (`youtube.search.list`). Discovery requires either a Google Developer API Key or the `https://www.googleapis.com/auth/youtube.readonly` OAuth scope.
- **Credential Storage Exposure**:
  - `token.json` exists in the repository root and contains live OAuth refresh tokens and client secrets.
  - `.gitignore` ignores `youtube_token.json`, `client_secrets.json`, and `credentials.json`, but **omits `token.json`**.
  - `youtube_uploader.py:59` contains a hardcoded fallback path searching `../youtube-agent-skill/youtube_token.json` outside the repository tree.

---

### 1.7 1080p 60FPS Benchmark & Sample Footage Audit
- **Benchmark Runner (`benchmark_runner.py`)**:
  - Successfully targets `input/benchmark_gta6_gameplay_1080p60.mp4` (166 MB, 45.0 seconds duration).
  - Probing confirms true 1080p 60 FPS: `h264 (Constrained Baseline), yuv420p, 1920x1080, 29.3 Mb/s, 60.0 fps, audio aac 44.1 kHz mono`.
  - Deficiencies: Does not capture CPU utilization, RAM consumption, or GPU metrics; does not verify that the output video retains 60.0 FPS.
- **Corrupted Workspace Sample**:
  - `projects/test_sample_video.mp4` (4.19 MB) was inspected. FFmpeg probing fails with `moov atom not found` (truncated file from interrupted download). It is unusable as a test fixture.
- **Automated Synthetic Fixture**:
  - `tests/test_e2e_pipeline.py:34-58` generates dynamic synthetic video using FFmpeg `lavfi` (`testsrc=duration=15:size=1280x720:rate=30` + `sine=frequency=440:duration=15`), providing an immaculate, self-contained testing pattern.

---

### 1.8 Existing Test Suite Baseline
Executing `pytest tests/` with the project Python 3.12 interpreter and FFmpeg configured produces:
- Total Test Suites: 10
- Total Tests: 49
- Results: **49 passed in 100.52 seconds (100% pass rate)**.
- Suites verified: `test_db.py` (4), `test_e2e_pipeline.py` (1), `test_ingestion_and_sources.py` (4), `test_metadata_and_youtube.py` (2), `test_publishing_and_hardening.py` (6), `test_publishing_security_gates.py` (8), `test_robustness_and_edge_cases.py` (6), `test_scene_and_analysis.py` (3), `test_semantic_analyzer.py` (11), `test_voice_and_subtitles.py` (4).

---

## 2. Existing vs. Missing Functionality Gap Analysis

### 2.1 Comprehensive Capability Matrix

| System Domain | Existing Repository Capability | Missing / Required Priority 5 Capability | Status |
|---|---|---|---|
| **Stream Discovery** | None. Mode B in `source_discovery.py` only registers local static files. | YouTube Data API v3 live search (`eventType='live'`, `categoryId=20`); quota caching; metadata persistence. | **MISSING** |
| **Footage Rights Separation** | Binary flag `permission_verified` in `sources` table for local files. | Architectural legal firewall: `AuthorizedSourceAdapter` interface; streams without authorized adapter are metadata-only. | **MISSING** |
| **Stream Ingestion** | Batch ingestion of full video files (`gameplay_ingestion.py`). | Rolling 10–15s chunk ingestion into bounded ring buffer (`livestream_monitor.py`); zero full-stream archive storage. | **MISSING** |
| **Concurrency & Resources** | Unbounded; synchronous execution; `-threads 0` consumes all CPU cores. | Hard caps: max 3 streams, max 2 workers; `-threads 4` CPU clamp; optional NVENC GPU; 10 GB disk ceiling. | **MISSING** |
| **Event Detection Latency** | Full-video batch sliding-window analysis (takes 30–90s per video). | Two-stage low-latency streaming detection: Stage 1 CV/audio filter (1–2s) $\to$ Stage 2 selective 3-keyframe VLM. | **MISSING** |
| **Frame Rate Handling** | Hardcoded `fps=30` in `config.py` and `action_fast` zoompan filter. | Conditional FPS: preserve 60 FPS when source $\ge 59$ FPS; natively support 30/25 FPS without frame duplication. | **MISSING** |
| **Audio Mixing & Norm** | Sidechain ducking operational. `bgm_audio` unused; `-af loudnorm` omitted. | Functional background music loop with ducking; EBU R128 (-14 LUFS) broadcast loudness normalization. | **INCOMPLETE** |
| **Publishing Safety** | 8-rule compliance check implemented in `publishing_policy.py`. | **Critical Fix**: Eliminate human approval bypass in `youtube_uploader.py`; enforce two-key upload requirement. | **VULNERABLE** |
| **Credential Security** | OAuth 2.0 flow works; simulation mode defaults to `True`. | Add `token.json` to `.gitignore`; support env vars for secrets; eliminate sibling directory probing. | **VULNERABLE** |
| **Database Concurrency** | Single-connection SQLite DAO in default rollback journal mode. | `PRAGMA journal_mode = WAL;`; `busy_timeout = 30000;`; versioned migration runner; 5 new tables. | **MISSING** |
| **Task Queue & Recovery** | Synchronous execution; zero background worker queue; zero restart recovery. | Persistent SQLite task queue (`processing_jobs`); `ApplicationRecoveryService` startup reconciler. | **MISSING** |
| **Dashboard & Web UI** | Synchronous FastAPI and Streamlit views for static local files. | Real-time views for Discovered Streams, Active Sessions, Queue Health, and non-blocking job submission. | **INCOMPLETE** |
| **CLI Management** | 9 commands for local file scanning, ingestion, clipping, and uploading. | New subcommands: `discover-streams`, `monitor`, `worker`, `recover`. | **INCOMPLETE** |
| **Automated Testing** | 49 unit and integration tests passing for batch pipeline. | 20-point comprehensive test suite covering multi-stream discovery, bounded buffers, FPS, gates, recovery. | **PLANNED** |

---

### 2.2 Anti-Duplication Directives (What to Preserve vs. What to Build)

To avoid rewriting mature, production-grade components, Priority 5 strictly adheres to the following preservation boundaries:

1. **DO NOT Rewrite Subtitle Generation**: `modules/subtitle_generator.py` already creates high-precision SRT and ASS karaoke subtitles with yellow highlight formatting and safe margin positioning (`MarginV: 480`). This module is reused without alteration.
2. **DO NOT Rewrite Speech Synthesis**: `modules/voice_generator.py` already implements multi-lingual Edge-TTS with word-boundary timestamp extraction and Windows SAPI fallback. It will be reused directly.
3. **DO NOT Rewrite the 8-Rule Policy Logic**: `modules/publishing_policy.py` has an exhaustive, well-tested 8-rule validation engine. The fix required is in `youtube_uploader.py` to ensure this engine is **never bypassed**.
4. **DO NOT Rewrite Temporal NMS**: `modules/highlight_ranker.py` has a robust 1D temporal IoU Non-Maximum Suppression algorithm. It will be imported directly by the streaming event detector.
5. **DO NOT Rewrite Scene Cut Mathematics**: The 160x90 4 FPS grayscale frame difference logic in `modules/scene_detector.py` is sound and fast. It will be extracted into a streaming chunk filter.

---

## 3. Multi-Stream Discovery Architecture

### 3.1 YouTube Data API v3 Two-Step Search & Viewer Count Specification
Stream discovery is encapsulated in a new module: `modules/livestream_discovery.py`. It polls the YouTube Data API v3 to discover active GTA 6 livestreams using a robust two-step discovery flow:

#### Step 1: Broad Search Query (`search.list`):
- **Endpoint**: `https://www.googleapis.com/youtube/v3/search`
- **HTTP Method**: `GET`
- **Cost**: **100 quota units**
- **Authentication**: API Key (`developerKey`) or OAuth 2.0 Token with `https://www.googleapis.com/auth/youtube.readonly` scope.
- **Query Parameters**:
  - `part`: `"snippet"` (returns video ID, title, channel ID, channel title, description, thumbnails, live broadcast status).
  - `eventType`: `"live"` (restricts search strictly to broadcasts currently streaming).
  - `type`: `"video"`.
  - `videoCategoryId`: `"20"` (Gaming category).
  - `q`: `"GTA 6" OR "Grand Theft Auto VI" OR "GTA VI"`.
  - `order`: `"viewCount"` (prioritizes high-audience broadcasts) or `"date"`.
  - `maxResults`: `10` (bounded to minimize payload).

#### Step 2: Batch Hydration of Viewer Counts & Live Details (`videos.list`):
Because `search.list` returns only basic snippet metadata and **does not provide concurrent viewer counts**, Step 1 is immediately followed by a batch `videos.list` call:
- **Endpoint**: `https://www.googleapis.com/youtube/v3/videos`
- **HTTP Method**: `GET`
- **Cost**: **1 quota unit** (per batch of up to 50 video IDs)
- **Query Parameters**:
  - `part`: `"snippet,liveStreamingDetails,statistics"`
  - `id`: Comma-separated list of video IDs returned by Step 1 (e.g. `"id1,id2,id3"`).
- **Extracted Fields**:
  - `liveStreamingDetails.concurrentViewers`: Parsed as integer viewer count.
  - `liveStreamingDetails.actualStartTime`: Live broadcast start timestamp.
  - `statistics.viewCount`: Total lifetime views.
- **Graceful Handling of Unavailable Viewer Counts**:
  - If a creator disables public viewer count displays, or if the stream is in a pre-live standby state, `concurrentViewers` will be omitted from the YouTube response.
  - The discovery engine explicitly handles this: `viewer_count` is set to `None` in the dataclass and `NULL` in SQLite.
  - The UI and CLI render `None` as `"N/A"` or `"Unavailable"`. The system **never crashes, never defaults to 0 as an assumed real value, and never fabricates synthetic viewer counts**.

---

### 3.2 Quota Economics, Intelligent Polling & Request Accounting
The YouTube Data API allocates a default project quota of **10,000 units per day**.
- A `search.list` request costs **100 units**.
- A `videos.list` batch request costs **1 unit**.
- An unmanaged polling loop running once per minute would execute 1,440 requests/day = **145,440 units/day** (instantly exhausting quota within 1.6 hours).

#### Quota Preservation Strategies & Budget Hardening:
1. **Configurable 30-Minute Discovery Polling (`YOUTUBE_DISCOVERY_POLL_INTERVAL_MINUTES = 30`)**:
   - Background discovery polling defaults to a **30-minute interval** (configurable via environment variable `YOUTUBE_DISCOVERY_POLL_INTERVAL_MINUTES`).
   - Hard-capped to **exactly 1 page (`max_pages = 1`, `maxResults = 10`)** per poll cycle. Auto-pagination (`nextPageToken` traversal) is strictly prohibited in background tasks.
   - At 30-minute intervals: 48 poll cycles per day.
   - 48 cycles $\times$ 100 units (`search.list`) = **4,800 units/day**.
   - 48 cycles $\times$ 1 unit (`videos.list` batch hydration) = **48 units/day**.
   - **Total Background Discovery Consumption**: **4,848 units/day** (48.48% of the 10,000 project quota).
2. **Dedicated Quota Buffer for Manual Discovery & Direct Verification**:
   - **1,000 units/day (10.0%)** is explicitly allocated as a dedicated budget for operator-initiated manual searches via the Web Dashboard or CLI (`cli.py discover-streams --query "..."`).
   - Direct single-stream status reconciliation checks cost only 1 unit per call (`videos.list`), consuming $< 50$ units/day.
   - **Remaining Reserve Buffer**: **4,102 units/day (41.02%)** is preserved for YouTube Shorts video uploads (1,600 units/upload) and quota safety margin.
3. **Comprehensive Request Accounting (`youtube_api_quota_usage`)**:
   - Every outbound YouTube API request is recorded in the `youtube_api_quota_usage` table with endpoint name, units consumed, caller context (`background_poll`, `manual_search`, `stream_status_check`, `upload`), and timestamp.
   - The service calculates remaining daily quota in real-time. If the daily budget is within 100 units of exhaustion, non-essential calls are blocked.
4. **Timezone-Aware Pacific Time Quota Reset (`America/Los_Angeles`)**:
   - YouTube API quotas strictly reset at midnight Pacific Time (**00:00:00 America/Los_Angeles** / 07:00:00 or 08:00:00 UTC depending on PDT/PST daylight saving).
   - Quota accounting evaluates calendar boundaries using Python's `zoneinfo.ZoneInfo("America/Los_Angeles")`. The daily usage counter resets automatically at 00:00:00 PT, avoiding premature lockouts or off-by-one errors from local UTC calculations.
5. **Local SQLite Caching**:
   - Results are cached in the `discovered_streams` table with a Time-To-Live (TTL) of **300 seconds** (5 minutes). Repeated calls within the TTL return cached records without making network requests.
6. **Exponential Backoff on Transient Errors**:
   - For network timeouts, DNS resolution issues, or HTTP 5xx responses (500, 502, 503, 504), the discovery client executes an exponential backoff routine:
     $$t_{\text{backoff}} = \min(60.0, \, 2^{\text{retry}} \times 2.0 + \text{uniform}(0, 1.0))$$
   - A maximum of **3 retries** is permitted within a single poll cycle. If all 3 retries fail, the poll cycle aborts without consuming additional quota, logging a warning and waiting for the next scheduled 30-minute interval.
7. **Circuit-Breaker on HTTP 403 `quotaExceeded`**:
   - When YouTube responds with HTTP 403 (`quotaExceeded`), the discovery service sets an internal circuit-breaker flag (`quota_exhausted = True`) and immediately suspends all external API calls until the next Pacific Time midnight reset.
   - During quota suspension, discovery queries transparently serve existing database records from `discovered_streams`.
8. **Decoupled Discovery Simulation Mode**:
   - Controlled independently by `LIVESTREAM_DISCOVERY_MOCK = True` (or `config.youtube.simulate_discovery`). When enabled, discovery generates synthetic mock streams for offline testing, consuming 0 API quota units.
   - When `LIVESTREAM_DISCOVERY_MOCK = False` and no API credentials exist, discovery raises an actionable error rather than silently fabricating mock records.

---

### 3.3 Stream Discovery Data Contract, Caching & Stale Stream Lifecycle Reconciliation

```python
@dataclass
class DiscoveredStreamMetadata:
    stream_video_id: str
    channel_id: str
    channel_title: str
    title: str
    thumbnail_url: str
    viewer_count: Optional[int]  # None if hidden, unavailable, or pre-live
    stream_start_time: Optional[datetime]
    is_live: bool
    discovered_at: datetime
    ended_at: Optional[datetime] = None
    has_authorized_source: bool = False
```

#### Service Interface Contract:
```python
class LivestreamDiscoveryService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl_seconds: int = 300,
        poll_interval_minutes: int = 30,
        manual_budget_units: int = 1000
    ):
        ...
    def discover_active_streams(
        self,
        query: str = "GTA 6",
        max_results: int = 10,
        max_pages: int = 1  # Hardcoded to 1 for background polling
    ) -> List[DiscoveredStreamMetadata]:
        """Executes Step 1 search.list followed by Step 2 videos.list batch hydration."""
        ...
    def check_stream_status(self, stream_video_id: str) -> Tuple[bool, Optional[datetime]]:
        """Directly queries videos.list (1 unit) to confirm if an individual stream is truly live or ended."""
        ...
    def sync_to_database(self, streams: List[DiscoveredStreamMetadata]) -> int:
        """Upserts discovered streams into discovered_streams table without altering footage rights."""
        ...
    def reconcile_stale_streams(self, active_stream_ids: Set[str]) -> int:
        """Confirms individual video status before marking any stream offline."""
        ...
```

#### Stale Stream Lifecycle Reconciliation Specification:
Livestreams can conclude at any moment between the 30-minute discovery poll cycles. Furthermore, a stream may drop out of a limited 10-result search response simply because other streams surpassed it in view count, even though it remains actively live.

**Strict Status Reconciliation Principle**:
**A stream must NEVER be marked offline merely because it disappeared from a limited `search.list` response.**

To enforce this, `reconcile_stale_streams()` executes a verified two-phase lifecycle confirmation protocol:

1. **Candidate Identification**:
   - Query `discovered_streams` for all records where `is_live = 1`.
   - Identify streams present in SQLite as live, but absent from the latest `search.list` top-10 result set:
     $$\text{CandidateEndedIDs} = \{ \text{id} \in \text{DB}_{\text{live}} \mid \text{id} \notin \text{Search}_{\text{top10}} \}$$
2. **Direct Individual / Batch Verification via `videos.list`**:
   - For each candidate ended stream, the service dispatches a targeted `videos.list(part="snippet,liveStreamingDetails", id=...)` query (cost: 1 unit per 50 videos).
   - If `items` is empty (video deleted/private), or `liveStreamingDetails.actualEndTime` is present, or `snippet.liveBroadcastContent == "none"`:
     - The stream is confirmed as **genuinely ended**.
   - If `liveStreamingDetails` confirms the stream is still broadcasting (`liveBroadcastContent == "live"`):
     - The stream remains marked as `is_live = 1`. Its metadata is refreshed, and active monitoring sessions continue uninterrupted.
3. **Database Lifecycle Transition**:
   - For confirmed ended streams, execute an atomic reconciliation update:
     ```sql
     UPDATE discovered_streams
     SET is_live = 0,
         ended_at = COALESCE(:actual_end_time, CURRENT_TIMESTAMP),
         last_polled_at = CURRENT_TIMESTAMP
     WHERE stream_video_id IN (:confirmed_ended_ids) AND is_live = 1;
     ```
4. **Active Session Graceful Termination**:
   - Query `monitoring_sessions` for any session linked to a confirmed ended stream where `session_status = 'active'`:
     ```sql
     UPDATE monitoring_sessions
     SET session_status = 'stopped',
         stopped_at = CURRENT_TIMESTAMP
     WHERE stream_id IN (
         SELECT id FROM discovered_streams WHERE stream_video_id IN (:confirmed_ended_ids)
     ) AND session_status = 'active';
     ```
   - Signal the corresponding `livestream_monitor` worker thread to conclude ingestion. The monitor thread flushes any remaining 10–15s chunks currently in the ring buffer, submits candidate keyframes for queued processing, and exits cleanly.
5. **Telemetry & Storage Housekeeping**:
   - Insert a final telemetry record in `stream_health` recording `status = 'offline'`.
   - Mark the stream's buffer directory (`output/buffer/stream_{stream_id}/`) as eligible for immediate garbage collection by `GarbageCollectionService`.

---

### 3.4 Discovery-Only Isolation Guarantee
The platform establishes a strict architectural and legal invariant:
$$\text{Discovery}(\text{Stream}) \implies \text{StoreMetadata}(\text{Stream}) \quad \not\implies \quad \text{AuthorizeAcquisition}(\text{Stream})$$

Under no circumstances does discovery trigger automated video downloading or stream recording. The stream metadata is written to `discovered_streams` with `has_authorized_source = 0`. The monitoring and clipping engines are strictly forbidden from connecting to or processing any stream where `has_authorized_source != 1`.

---

## 4. Footage Acquisition Separation & Legal Compliance

### 4.1 Architectural Decoupling: Discovery vs. Acquisition
Public stream metadata and video stream acquisition are separated by an explicit abstraction layer. The following diagram illustrates this legal firewall:

```
┌────────────────────────────────────────────────────────┐
│              YouTube Data API v3 Discovery             │
│            (Public Search & Metadata Only)             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
           ┌──────────────────────────────────┐
           │     discovered_streams Table     │
           │  (Video ID, Title, Channel, etc) │
           └────────────────┬─────────────────┘
                            │
          [Is Stream Authorized in DB?]
          ├─────────────── NO ───────────────► [Status: "Metadata Only"]
          │                                    [Action: DISPLAY IN DASHBOARD]
          │                                    [FORBIDDEN: Download / Capture]
         YES
          │
          ▼
┌────────────────────────────────────────────────────────┐
│             AuthorizedSourceAdapter Interface          │
│       (Permitted Feeds, Owned Files, Licensed Media)   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
           ┌──────────────────────────────────┐
           │      livestream_monitor.py       │
           │  (Bounded Rolling Ring Buffer)   │
           └──────────────────────────────────┘
```

---

### 4.2 The AuthorizedSourceAdapter Interface Specification

To enforce this separation in code, all video acquisition must implement the `AuthorizedSourceAdapter` abstract base class in `modules/authorized_source_adapter.py`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

class UnauthorizedFootageError(PermissionError):
    """Raised when an attempt is made to acquire footage without verified authorization."""
    pass

@dataclass
class ChunkMetadata:
    chunk_index: int
    start_timestamp: float
    duration_seconds: float
    filepath: Path
    bitrate_kbps: float
    fps: float
    has_audio: bool

class AuthorizedSourceAdapter(ABC):
    @abstractmethod
    def verify_authorization(self, stream_video_id: str) -> bool:
        """
        Validates that verified legal permission exists in the database
        for this stream's channel or source. Returns True only if
        authorized_footage_sources contains a verified record.
        """
        pass

    @abstractmethod
    def acquire_stream_chunk(
        self,
        stream_video_id: str,
        chunk_duration_sec: float,
        destination_path: Path
    ) -> ChunkMetadata:
        """
        Acquires a discrete 10-15s chunk from an authorized feed.
        MUST raise UnauthorizedFootageError if verify_authorization() returns False.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleanly releases network sockets, hardware decoders, or sub-processes."""
        pass
```

---

### 4.3 Concrete Acquisition Adapters, Credential Hardening & Candidate Admission Throttling
Four concrete adapters implement this interface, binding verified legal records and concrete connection endpoints:

1. **`CreatorAuthorizedStreamAdapter`**:
   - Ingests an authenticated RTMP, SRT, or WebRTC feed directly provided by a collaborating creator via `feed_endpoint_url` (e.g., `rtmp://live.creator.net/app` or `srt://stream.partner.tv:9000`).
   - **Zero Raw Secrets in Database**: Stream keys and authentication tokens are **NEVER stored in plain text in SQLite**. `authorized_footage_sources.stream_key_secret_ref` stores only a secret reference URI (e.g. `"ENV:CREATOR_A_STREAM_KEY"` or `"VAULT:CREATOR_A_KEY"`).
   - At runtime, the adapter resolves the secret reference from system environment variables or secure storage.
   - When launching FFmpeg subprocesses, the resolved secret is transmitted securely via standard input (`stdin`) or an internal pipe—**never exposed as a command-line argument**, preventing credential leakage in process listings (`ps`, Task Manager).
   - Enforces creator authorization records stored in `authorized_footage_sources`, verifying that `permission_verified = 1`, `commercial_reuse_allowed = 1`, and `derivative_editing_allowed = 1`.
2. **`UserOwnedRecordingAdapter`**:
   - Ingests gameplay footage recorded directly by the user/operator via local capture hardware (OBS, Elgato, Blackmagic) or local MP4 files.
   - Binds to `feed_endpoint_url` representing a verified local capture path or local OBS virtual camera pipe.
   - Validates that the file exists in an authorized local capture folder and matches user-owned copyright declarations.
3. **`RockstarPressKitAdapter`**:
   - Ingests official Rockstar Games promotional and trailer video assets explicitly released for press and content creator usage under fair use and press terms.
   - Binds to verified local press kit directories or official download mirrors with SHA256 integrity validation.
4. **`SyntheticMockStreamAdapter`**:
   - Used for continuous integration and unit testing. Generates synthetic 60 FPS / 30 FPS video chunks using FFmpeg `lavfi` patterns (`testsrc2`, `sine`) without external network calls.
   - Strictly active only when `FOOTAGE_ACQUISITION_SIMULATION = True`.

#### Decoupled Tri-Simulation Architecture & Graceful Failures:
Simulation behavior is cleanly decoupled into three independent configuration settings:
1. `YOUTUBE_UPLOAD_SIMULATION: bool` (defaults to `True`; mocks YouTube Data API upload calls).
2. `LIVESTREAM_DISCOVERY_MOCK: bool` (defaults to `True` for offline testing; mocks search responses).
3. `FOOTAGE_ACQUISITION_SIMULATION: bool` (defaults to `True` for offline testing; generates synthetic video chunks).

**Graceful Actionable Error Invariant**:
When a simulation flag is toggled to `False` (Production / Real Network Mode), the system **strictly disables synthetic fallbacks**. If required credentials, stream keys, or network endpoints are missing or invalid:
- The system immediately raises an actionable, human-readable error (e.g., `ConfigurationError: Creator stream key reference 'ENV:CREATOR_A_STREAM_KEY' not found in environment. Set this variable or enable FOOTAGE_ACQUISITION_SIMULATION=1.`).
- It **never silently falls back to synthetic mock data** while claiming real production acquisition.

#### Candidate Clip Admission Throttling Specification:
In open-world gameplay, extended high-action sequences (e.g., a 10-minute continuous 5-star police chase or prolonged shootout) can generate high heuristic scores for dozens of consecutive 12-second chunks. Unconstrained candidate admission would rapidly flood the candidate storage directory, generating gigabytes of intermediate files and breaching the 10 GB disk cap within 30 minutes.

To guarantee bounded disk utilization and prevent candidate generation bursts, the ingestion pipeline implements a four-tiered **Candidate Admission Governor**:

1. **Minimum Inter-Candidate Cooldown (Temporal Governor)**:
   - Enforces a mandatory cooldown of **maximum 1 candidate clip per 60 seconds per stream**.
   - When a 12-second chunk is admitted as a candidate, an admission timestamp is recorded for that stream.
   - Any subsequent chunk arriving within the 60-second cooldown window is suppressed from candidate admission and ring-buffer promotion unless its heuristic score reaches an **Emergency Breakthrough Threshold** ($S_{\text{heuristic}} \ge 90.0$).
2. **Dynamic Heuristic Threshold Raising (High-Density Action Adaptation)**:
   - The baseline heuristic admission threshold is $S_{\text{heuristic}} \ge 65.0$.
   - The stream monitor maintains a sliding 5-minute window counting admitted candidates.
   - If candidate admission density increases, the threshold automatically escalates:
     - $\le 3$ candidates in 5 min $\implies$ Baseline threshold $S_{\text{heuristic}} \ge 65.0$.
     - 4th candidate in 5 min $\implies$ Escalated threshold $S_{\text{heuristic}} \ge 75.0$.
     - 5th candidate in 5 min $\implies$ High-action threshold $S_{\text{heuristic}} \ge 82.0$.
     - $\ge 6$ candidates in 5 min $\implies$ Maximum burst threshold $S_{\text{heuristic}} \ge 88.0$.
   - When gameplay intensity decreases (zero candidates admitted for 3 minutes), the threshold smoothly decays back toward $65.0$ at a rate of **2.0 points per minute**.
3. **Storage-Aware Admission Shedding (Disk Cap Protection)**:
   - Before admitting any candidate, the governor probes current disk usage in `output/buffer/` and `output/candidates/`:
     - **Normal Range ($< 7.0$ GB)**: Standard admission rules apply.
     - **Elevated Range ($7.0 \text{ GB} \le \text{Usage} < 8.5\text{ GB}$)**: Admission threshold is forced to a minimum of **$80.0$**, and cooldown is extended to **120 seconds**.
     - **Emergency Ceiling ($\ge 8.5$ GB)**: Candidate admission is **completely frozen** (100% shedding). Chunks remain strictly within the 5-chunk ring buffer until background rendering completes and `GarbageCollectionService` reclaims storage below 6.0 GB.
4. **Ring Buffer Overwrite Protection**:
   - Chunks that are not admitted as candidates are never copied to `output/candidates/`. They reside solely in the 5-chunk rolling ring buffer (`output/buffer/stream_{stream_id}/`), which naturally overwrites older unpinned chunks every 12 seconds, maintaining a strict constant disk footprint of $\approx 15$ MB per active stream.

---

### 4.4 Legal Evidence Verification, Access Logging & Dashboard Gating
In the database, footage acquisition requires an entry in `authorized_footage_sources` satisfying a strict multi-attribute evidence schema:
- `permission_verified = 1`: Explicit verification flag.
- `creator_identity`: Verified legal or channel name of the rights holder.
- `evidence_type IN ('WRITTEN_CREATOR_PERMISSION', 'CREATIVE_COMMONS_VERIFIED', 'USER_ORIGINAL_FOOTAGE', 'OFFICIAL_PRESS_KIT')`.
- `evidence_url_or_doc`: Signed contract reference, SHA256 document hash, or verifiable Creative Commons URL (placeholder text strictly rejected).
- `permission_scope`: Explicit enumeration of permitted rights (e.g. `"live_clipping,vertical_video_derivatives,youtube_shorts_distribution"`).
- `commercial_reuse_allowed = 1`: Explicit confirmation of commercial monetization rights.
- `derivative_editing_allowed = 1`: Explicit confirmation of transformative commentary and editing rights.
- `expiration_date`: Legal expiration timestamp (acquisition rejected if `CURRENT_TIMESTAMP >= expiration_date`).
- `verified_by`: Identity of the compliance officer or auditor approving the source.

#### Access Audit Logging (`source_access_records`):
Every time an adapter connects to an authorized stream feed or accesses video chunks, it writes an immutable audit record into `source_access_records`:
- `source_id`: Foreign key to `authorized_footage_sources`.
- `session_id`: Active monitoring session identifier.
- `chunk_index`: Sequence number of the accessed video chunk.
- `accessed_at`: Timestamp of chunk acquisition.
- `bytes_transferred`: Byte count of acquired video.
- `purpose`: Operational tag (e.g. `"streaming_event_detection"`).

#### Dashboard Evidence Presentation & Fail-Closed Gating:
1. **Visual Evidence Card**:
   - In the Web Dashboard (`web_app.py`) and Streamlit (`app.py`), discovered streams linked to verified sources display a green **"AUTHORIZED FEED"** badge.
   - Clicking the badge opens an **Evidence Inspector Modal** displaying the rights holder, license category, document hash/URL, permitted scope, and expiration date.
2. **Metadata-Only Enforcement**:
   - Streams lacking verified evidence display a prominent red **"METADATA ONLY — UNLICENSED"** badge.
   - The "Start Monitoring" and "Extract Clip" buttons are disabled in the UI.
3. **Extraction & Candidate Blocking**:
   - If an unauthorized stream is targeted via CLI or API, `AuthorizedSourceAdapter.verify_authorization()` returns `False`.
   - The monitoring engine immediately raises `UnauthorizedFootageError`, refusing to allocate buffer directories, connect to the feed, or extract candidate highlights.
4. **Non-Overridable Legal Rule**:
   - **Human approval can NEVER override missing or invalid source authorization.** If a candidate clip is somehow submitted without verified source evidence, the Tier 1 publishing gate strictly rejects upload, regardless of operator approval.

---

## 5. Concurrent Stream Processing & Bounded Resource Policies

### 5.1 Bounded Rolling Chunk Ring Buffer Architecture & Context Pinning (10–15s Chunks)
To process 5–24 hour livestreams without filling workstation disks, `modules/livestream_monitor.py` implements a **bounded rolling ring buffer with intelligent context pinning**.

#### Ring Buffer Specification:
- **Chunk Duration**: Fixed at **10.0 to 15.0 seconds** (configurable in `config.py:StreamSettings.chunk_duration_seconds = 12.0`).
- **Buffer Retention Window**: Baseline of **5 chunks** (approx. 60 seconds of video) retained in the active ring buffer per monitored stream.
- **Buffer Storage Directory**: `output/buffer/stream_{stream_id}/chunk_{index}.mp4`.
- **Intelligent Context Pinning (`is_pinned = True`)**:
  - Highlights rarely start and stop cleanly within a single 12-second window. A high-action event (such as an explosion or vehicle crash) detected in chunk $C_i$ often has crucial build-up in preceding chunks ($C_{i-2}, C_{i-1}$) and consequential aftermath in subsequent chunks ($C_{i+1}, C_{i+2}$).
  - When Stage 1 detects a candidate highlight in chunk $C_i$:
    1. The monitor marks preceding chunks $C_{i-2}, C_{i-1}$ as **pinned** (`is_pinned = True`).
    2. Chunk $C_i$ is pinned.
    3. The monitor arms forward-pinning for incoming subsequent chunks $C_{i+1}, C_{i+2}$.
  - **Eviction Immunity**: Pinned chunks are **strictly immune from ring buffer deletion and FIFO rotation**. Even if the stream monitor acquires dozens of subsequent chunks, pinned chunks remain locked on disk.
  - **Extraction & Unpinning**: Once the background worker stitches the full composite highlight (spanning $[C_{i-2} \dots C_{i+2}]$) and extracts the candidate clip, the chunks are marked `is_pinned = False` and become eligible for immediate garbage collection.
- **Bounded Candidate Retention & Queue Limits**:
  - To prevent runaway queue growth under extended action sequences, the system enforces a hard ceiling of **maximum 50 active candidate clips** across all queues and candidate storage.
  - If the active candidate count reaches 50, further candidate promotion is paused until background workers process and render queued clips.

```
Incoming Stream Feed
        │
        ▼
[Acquire Chunk N (12s)] ───► [Stage 1 CV/Audio Filter (1.5s Target)]
        │                                 │
        │                   Score < 65.0? │ Score >= 65.0 (Event Detected)?
        │                         │                  │
        ▼                         ▼                  ▼
[Write to Ring Buffer]   [Recycle Chunk N]   [Pin Context Chunks (N-2..N+2)]
        │                                            │
[Is Chunk N-5 Unpinned?]                             ▼
        │                                    [Enqueue Async VLM Job]
       YES                                           │
        ▼                                            ▼
[Delete Chunk N-5 from Disk]                 [Extract Composite Highlight]
                                                     │
                                                     ▼
                                             [Unpin Chunks N-2..N+2]
```

---

### 5.2 Hard Resource Caps, Concurrency Limits & Asynchronous Decoupling
Workstation stability is protected through hard limits in `config.py`:

```python
@dataclass
class ResourceLimits:
    max_concurrent_streams: int = 3       # Max simultaneous livestream monitor threads
    max_concurrent_workers: int = 2       # Max background video rendering / inference jobs
    max_active_candidates: int = 50       # Hard ceiling on pending highlight candidates
    ffmpeg_cpu_threads: int = 4           # FFmpeg thread clamp (replaces -threads 0)
    max_disk_usage_gb: float = 10.0       # Max disk usage for candidate clips & buffers
    min_disk_free_gb: float = 5.0         # Emergency pause threshold if drive space drops
    temp_chunk_ttl_minutes: int = 15      # Retention limit for intermediate buffer chunks
    candidate_retention_hours: int = 48   # Auto-purge unapproved candidates after 48h
```

#### Performance Characterization Notice & Hardware Benchmarking Mandate:
> [!IMPORTANT]
> **All performance metrics, execution latencies, and storage bounds stated in this plan (such as 1.0–1.5s Stage 1 filter latency, 2.0s monitor cycle time, and 10 GB disk envelopes) are PRELIMINARY TARGET ESTIMATES based on single-stream synthetic tests, NOT proven production hardware facts.**
> 
> Production deployment mandates empirical hardware and network benchmarking under real concurrent streams. Phase 12 (Milestone M9 / R12) explicitly requires comprehensive instrumentation logging:
> - **CPU Utilization**: Core saturation and thread contention under multi-stream load.
> - **System RAM**: Resident set size (RSS) and memory stability across 24-hour continuous runs.
> - **GPU VRAM & Decode Engines**: NVENC/CUDA utilization during simultaneous ingestion and 1080p60 encoding.
> - **Disk I/O Throughput**: Read/write IOPS and megabytes/sec during parallel chunk rolling and candidate extraction.
> - **Network Bandwidth**: Ingestion bitrate stability and packet drop rates across concurrent RTMP/SRT feeds.
> - **End-to-End Latency**: Wall-clock duration from live gameplay occurrence to completed 1080x1920 Short.

#### Asynchronous Decoupling Architecture:
The livestream monitoring engine (`modules/livestream_monitor.py`) and the heavy video/AI processing pipelines are strictly decoupled across two distinct execution tiers:

1. **Lightweight, Non-Blocking Monitor Tier**:
   - Up to 3 concurrent stream monitor threads (`max_concurrent_streams = 3`) run continuously.
   - Each monitor thread acquires 12-second chunks and executes Stage 1 CV/Audio heuristic filtering in 1.0–1.5 seconds (target).
   - If a chunk passes the heuristic threshold and satisfies the Candidate Admission Governor, the thread pins context chunks, writes a `vlm_inference` task into the `processing_jobs` SQLite table, and **immediately returns to acquire Chunk $N+1$**.
   - Under no circumstances does the monitor thread await local Ollama VLM inference (which requires 5–45 seconds). The total processing overhead in the monitor loop remains strictly bounded below **$2.0\text{ seconds}$ per 12-second chunk** (target), eliminating buffer underruns, network backpressure, and dropped stream packets.
2. **Dedicated Background Worker Tier**:
   - A persistent worker pool bounded by `max_concurrent_workers = 2` consumes tasks from the `processing_jobs` table.
   - Workers execute compute-heavy operations asynchronously: Stage 2 keyframe VLM inference, Edge-TTS audio synthesis, ASS subtitle generation, 1080x1920 vertical video composition, and policy compliance verification.
   - If local VLM inference stalls or encounters an extended inference queue, only the background queue latency increases; live stream acquisition continues uninterrupted in real-time.

---

### 5.3 CPU Thread Governance & Optional GPU Hardware Acceleration
- **CPU Throttling**: In all FFmpeg commands across `clip_generator.py`, `video_editor.py`, and `scene_detector.py`, the hardcoded `-threads 0` (which consumes 100% of all logical CPU cores) is replaced with:
  ```python
  "-threads", str(config.resources.ffmpeg_cpu_threads) # Defaults to 4 threads
  ```
- **Optional NVENC GPU Acceleration**:
  - `config.py` introduces `video_codec_preferred: str = "auto"` ("auto", "h264_nvenc", "libx264").
  - On startup, the system probes for NVIDIA NVENC capability via `ffmpeg -encoders | grep h264_nvenc`.
  - If NVENC is available and enabled:
    - Video encoding uses `-c:v h264_nvenc -preset p4 -rc vbr -cq 19 -b:v 15M`.
    - Scaling and color grading leverage CUDA filters when hardware decoding is active.
  - If NVENC is unavailable, the pipeline falls back gracefully to CPU `libx264 -preset fast -crf 18`.

---

### 5.4 Storage Thresholds, Candidate Admission Throttling & Deterministic Garbage Collection
A background maintenance routine (`GarbageCollectionService`) executes every 10 minutes (or immediately upon disk warning events):

1. **Storage Cap Enforcement & Candidate Admission Coordination (10 GB Hard Limit)**:
   - Calculates total disk consumption across `output/buffer/` and `output/candidates/`.
   - Coordinates in real-time with the **Candidate Admission Governor** (Section 4.3):
     - **Normal Operating Range ($< 7.0$ GB)**: Standard admission cooldown (60 seconds) and baseline heuristic threshold ($S_{\text{heuristic}} \ge 65.0$).
     - **Elevated Range ($7.0 \text{ GB} \le \text{Usage} < 8.5\text{ GB}$)**: Dynamic admission threshold raised to minimum **$80.0$**, inter-candidate cooldown extended to **120 seconds**, and lower-priority background tasks paused.
     - **Critical Disk Ceiling ($\ge 8.5$ GB)**: Candidate admission is **completely frozen** (100% shedding). Incoming stream chunks are strictly recycled inside the 5-chunk ring buffer without disk promotion until `GarbageCollectionService` reclaims storage below 6.0 GB.
2. **Automated Purging Rules**:
   - If total size exceeds `max_disk_usage_gb` (10 GB) or drive free space drops below `min_disk_free_gb` (5 GB):
     - Immediately purges all buffer chunks older than `temp_chunk_ttl_minutes` (15 minutes).
     - Purges candidate clips marked `rejected` or `purged` in the `clips` database table.
     - Purges unapproved candidate clips older than `candidate_retention_hours` (48 hours).
3. **Deterministic Temporary File Cleanup**:
   - Uses deterministic Python context managers (`try...finally`) in video and audio processors to guarantee temporary `.wav`, `.aac`, and intermediate keyframe `.jpg` files are deleted immediately after rendering completes.

---

## 6. Low-Latency Two-Stage Event Detection

### 6.1 High-Throughput Streaming Event Pipeline Overview
In a live broadcast, waiting for a 35-second sliding window over an entire video is unacceptable. The streaming detector processes incoming **12-second chunks** within **1–2 seconds of chunk arrival** using a two-stage funnel:

```
Incoming 12s Stream Chunk
           │
           ▼
┌────────────────────────────────────────────────────────┐
│     STAGE 1: Ultra-Fast Heuristic Filter (1–2s)        │
│  - Downscaled Pixel Difference (160x90 @ 4 FPS)        │
│  - Audio Energy RMS Spikes (0.5s intervals)            │
│  - Metric: S_heuristic = 0.6*Motion + 0.4*Audio        │
└──────────────────────────┬─────────────────────────────┘
                           │
                 [Passes Dynamic Heuristic & Admission Throttle?]
                 ├───────── NO ─────────► [Recycle in Ring Buffer (No Disk Growth)]
                YES
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│     Fast Candidate Admission & Asynchronous Queue      │
│  - Copy Chunk to output/candidates/                    │
│  - Extract 3 Monotonic Keyframes (<0.3s)               │
│  - Enqueue 'vlm_inference' Job in processing_jobs      │
│  - Stream Monitor Loop Returns Immediately (<2.0s)     │
└──────────────────────────┬─────────────────────────────┘
                           │ (Asynchronous Decoupling via DB Queue)
                           ▼
┌────────────────────────────────────────────────────────┐
│     STAGE 2: Selective Semantic AI Evaluation (Worker) │
│  - Background Worker Dequeues Task from DB             │
│  - Local VLM Inference (Moondream/Qwen Vision)         │
│  - Structured Scoring: Stunt, Humor, Cinematic         │
│  - Factual Fallback on Timeout (Tier 2 Editorial Rule) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│      Temporal IoU Non-Maximum Suppression (NMS)        │
│  - Deduplicates overlapping events (IoU > 0.30)        │
│  - Ranks composite highlights into Render Queue        │
└────────────────────────────────────────────────────────┘
```

---

### 6.2 Stage 1: Fast Heuristic CV & Audio Filtering (1–2s per Chunk)
`modules/scene_detector.py` and `modules/video_analyzer.py` are adapted to operate directly on 12-second chunk files:

1. **Visual Motion Delta**:
   - Frames are streamed via FFmpeg pipe downscaled to $160 \times 90$ at 4 FPS in `rgb24` rawvideo.
   - For a 12-second chunk, exactly 48 frames are analyzed.
   - Consecutive frames are converted to grayscale: $Y = 0.299 R + 0.587 G + 0.114 B$.
   - Mean absolute pixel difference $\Delta_i = \frac{1}{N} \sum |Y_{i} - Y_{i-1}|$ is computed via NumPy.
   - Visual motion score:
     $$M_{\text{visual}} = \min\left(100.0, \, \frac{\max(\Delta_i)}{\text{motion\_scale}} \times 100.0\right)$$
2. **Audio Energy RMS**:
   - Audio is extracted via FFmpeg pipe in 16 kHz 16-bit mono PCM.
   - RMS is calculated across 0.5-second windows (8,000 samples).
   - Audio energy score:
     $$A_{\text{audio}} = \min\left(100.0, \, (\text{RMS}_{\text{dB}} + 60.0) \times \frac{100.0}{60.0}\right)$$
3. **Stage 1 Heuristic Threshold & Asynchronous Task Enqueueing**:
   $$S_{\text{heuristic}} = 0.60 \times M_{\text{visual}} + 0.40 \times A_{\text{audio}}$$
   - **Admission Evaluation**: The chunk is evaluated against the Candidate Admission Governor (Section 4.3):
     - If $S_{\text{heuristic}} < \text{threshold}_{\text{dynamic}}$ (baseline $65.0$), or if the stream is in inter-candidate cooldown ($<60\text{s}$ since last admitted clip) and $S_{\text{heuristic}} < 90.0$, the chunk is not promoted. It remains in the ring buffer and is recycled naturally.
   - **Non-Blocking Asynchronous Enqueueing**:
     - If the chunk passes heuristic admission and disk usage $< 8.5$ GB, the monitor thread immediately copies the chunk to `output/candidates/candidate_{stream_id}_{chunk_index}.mp4`.
     - Extracts the 3 candidate keyframes (Hook, Peak, Climax) in $<0.3$ seconds.
     - Inserts a new background job into SQLite `processing_jobs` (`job_type = 'vlm_inference'`, payload containing stream ID, chunk index, candidate file path, keyframe paths, and Stage 1 heuristic metrics).
     - **The monitor loop NEVER awaits VLM inference.** It immediately returns to ingest Chunk $N+1$, ensuring the stream monitoring loop remains strictly non-blocking ($<2.0\text{s}$ execution time per 12-second chunk) with zero stream starvation.

---

### 6.3 Stage 2: Selective Semantic AI Gameplay Analysis (Keyframe VLM) & Fallback Semantics
Candidate chunks enqueued by the monitor loop are consumed asynchronously by the background worker pool (`max_concurrent_workers = 2`) via `modules/semantic_analyzer.py`:

1. **Worker Job Acquisition & Keyframe Loading**:
   - A background worker acquires the queued `vlm_inference` job atomically from `processing_jobs`.
   - Reads the 3 pre-extracted keyframes:
     - Frame 1 (Hook Frame): Timestamp $t_{\text{start}} + 0.8\text{s}$.
     - Frame 2 (Action Peak Frame): Timestamp of $\max(\Delta_i)$ identified in Stage 1.
     - Frame 3 (Climax / Outcome Frame): Timestamp $t_{\text{end}} - 1.0\text{s}$.
     - Monotonic sequence verification: $t_{\text{start}} \le t_1 < t_2 < t_3 \le t_{\text{end}}$.
2. **VLM Query & Parsing**:
   - Extracted JPEG bytes are submitted to the local Ollama instance (`http://localhost:11434/api/generate`) with a 5.0-second connection timeout and 45.0-second inference timeout.
   - Prompts for structured JSON rating `stunt_score` (0–100), `humor_score` (0–100), `cinematic_score` (0–100), `event_summary`, and `suggested_hook`.
3. **Factual Fallback Mechanism & Rule Hierarchy Classification**:
   - If Ollama is offline or times out, the analyzer activates the factual fallback protocol:
     - `stunt_score = 50.0`, `humor_score = 55.0`, `cinematic_score = 60.0`
     - Composite: $S_{\text{semantic}} = 0.40(50) + 0.35(55) + 0.25(60) = 54.25$
     - `event_summary = "GTA 6 gameplay sequence"`
     - `is_fallback = True`, `semantic_status = "FALLBACK"`
   - **Publishing Semantics (Tier 1 Invariants vs. Tier 2 Editorial Rules)**:
     - In the fail-closed Two-Key Gate hierarchy (detailed in Section 8.2), Rule 3 (`Semantic Valid`) is classified as a **Tier 2 (Reviewable Editorial Rule)**, not a Tier 1 legal invariant.
     - When a clip has `semantic_status == "FALLBACK"`, automated direct-publishing is strictly blocked to prevent unreviewed synthetic commentary from reaching public feeds.
     - However, **an authorized human operator reviewing the clip in the dashboard or CLI CAN grant explicit approval (`approved_for_upload = 1`), overriding the Tier 2 editorial fallback block and permitting publication of approved fallback commentary**.
     - **Non-Overridable Legal Invariant Guarantee**: Human approval can override Tier 2 editorial fallback rules, but can **NEVER override Tier 1 Legal & Media Invariants** (Rule 2 Source Rights Verified, Rule 4 Physical Media Specs, Rule 5 Duplicate Check, Rule 6 Metadata Presence). If source authorization is missing or video specs fail, the clip strictly fails closed regardless of human approval.

---

### 6.4 Temporal IoU Non-Maximum Suppression (NMS) & Highlight Ranking
When consecutive chunks both exhibit high action (e.g., a 25-second car chase spanning Chunk 4 and Chunk 5), they are merged into a single coherent candidate segment:
1. Candidate segments are mapped as 1D temporal intervals $[t_{\text{start}}, t_{\text{end}}]$.
2. Temporal Intersection-over-Union (IoU) is computed:
   $$\text{IoU}(A, B) = \frac{\max(0, \, \min(A_{\text{end}}, B_{\text{end}}) - \max(A_{\text{start}}, B_{\text{start}}))}{\max(A_{\text{end}}, B_{\text{end}}) - \min(A_{\text{start}}, B_{\text{start}})}$$
3. If $\text{IoU} > 0.30$, overlapping intervals are merged, and the composite engagement score is updated using `modules/highlight_ranker.py`.
4. The top $N$ unique, non-overlapping highlights are queued for rendering.

---

## 7. Conditional Frame Rate Handling

### 7.1 The Frame Rate Preservation Principle
YouTube Shorts natively supports 60 FPS video. High-motion open-world gameplay in GTA 6 (car chases, helicopter flights, shootouts) suffers severe visual judder when downsampled to 30 FPS. Conversely, forcing 30 FPS or 25 FPS source footage to render at 60 FPS causes FFmpeg to artificially duplicate frames, wasting encode time, memory, and disk space without visual benefit.

**The Conditional Rule**:
$$\text{Output FPS} = \begin{cases} 60 & \text{if } \text{Source FPS} \ge 59.0 \\ 30 & \text{if } 29.0 \le \text{Source FPS} < 59.0 \\ \text{round}(\text{Source FPS}) & \text{otherwise (e.g. 24, 25)} \end{cases}$$

---

### 7.2 Source Frame Rate Probing & Target Calculation
A dedicated probing utility is implemented in `modules/video_editor.py` and `modules/clip_generator.py`:

```python
def probe_source_fps(video_path: Path) -> float:
    """Probes exact container and stream framerate using ffprobe."""
    cmd = [
        config.FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe") if "ffmpeg.exe" in config.FFMPEG_PATH else "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,avg_frame_rate",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(res.stdout)
    stream = data["streams"][0]
    r_fps = stream.get("r_frame_rate", "30/1")
    num, den = map(float, r_fps.split("/"))
    return num / den if den != 0 else 30.0

def determine_target_fps(source_fps: float) -> int:
    """Calculates conditional target FPS without artificial frame duplication."""
    if source_fps >= 59.0:
        return 60
    elif source_fps >= 29.0:
        return 30
    else:
        return int(round(source_fps))
```

---

### 7.3 Filtergraph Modifications & Elimination of Hardcoded 30 FPS
Audit of `modules/video_editor.py:100` revealed a hardcoded bug in the `action_fast` template:
```python
# EXISTING BUG in video_editor.py:100
zoom_str = f",zoompan=z='min(zoom+0.0005,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
```
Even on 60 FPS benchmark gameplay, this filter forcibly downsampled the video to 30 FPS.

#### Fix Specification:
1. Dynamic parameter injection in `build_filtergraph`:
   ```python
   target_fps = determine_target_fps(source_fps)
   zoom_str = (
       f",zoompan=z='min(zoom+0.0005,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={target_fps}"
       if template.get("zoom_effect") else ""
   )
   ```
2. The final FFmpeg command dynamically appends:
   ```python
   "-r", str(target_fps)
   ```
   ensuring the container timebase matches the target frame rate cleanly.

---

## 8. Fail-Closed Publishing Safety & Security Hardening

### 8.1 Forensic Analysis of the Critical Bypass Vulnerability
In `modules/youtube_uploader.py:164–184`, the existing publishing authorization check was structured as follows:

```python
# VULNERABLE EXISTING CODE in youtube_uploader.py:164-184
if should_enforce:
    clip = db.get_clip_by_id(clip_id) if clip_id else None
    is_approved = clip and (
        clip.get("approved_for_upload") == 1
        or clip.get("status") in ("approved", "published")
    )
    if not is_approved:
        policy_eval = publishing_policy.evaluate(...)
        if not policy_eval.can_publish:
            # REJECT UPLOAD
            return UploadResult(success=False, ...)
```

#### The Critical Security Vulnerability:
If `is_approved` was `True` (`approved_for_upload == 1` or `status == "approved"`), **`publishing_policy.evaluate()` was completely skipped**.
Because `cli.py approve <id>` and `web_app.py POST /api/clips/{id}/approve` set `approved_for_upload = 1` without validating copyright or media integrity, an operator could approve any clip with **missing copyright permission**, **missing audio**, or **corrupted video**, and `youtube_uploader.py` would publish it to YouTube.

Furthermore, existing tests in `test_publishing_security_gates.py:101-114` and `test_publishing_and_hardening.py:256-266` actively relied on this flaw to pass tests with dummy 25-byte files.

---

### 8.2 The Fail-Closed Two-Key Gate Architecture & Rule Hierarchy
Priority 5 eliminates publishing bypasses by establishing a strict, formally tiered **Two-Key Authorization Gate**:

$$\text{CanUpload} = (\text{Key}_1: \text{HumanApproved} == \text{True}) \quad \mathbf{AND} \quad (\text{Key}_2: \text{PolicyPassed} == \text{True})$$

#### Tier 1 vs. Tier 2 Rule Hierarchy Specification:
To eliminate ambiguity between legal compliance and editorial quality, the 8 validation rules of `PublishingPolicy` are formally partitioned into two distinct tiers:

| Tier | Category & Name | Evaluation Scope | Human Override Semantics |
|---|---|---|---|
| **Tier 1** | **Rule 2: Source Rights & Copyright** | Verified permission (`permission_verified = 1`), valid license evidence URL/document, commercial reuse allowed. | **STRICTLY FORBIDDEN (NON-OVERRIDABLE)**. Human approval can NEVER bypass missing rights. |
| **Tier 1** | **Rule 4: Physical Media Specifications** | Container format (MP4), vertical 9:16 resolution (1080x1920), duration (15.0s to 60.0s), H.264 video stream present, AAC audio stream present. | **STRICTLY FORBIDDEN (NON-OVERRIDABLE)**. Corrupted or invalid media can NEVER be uploaded. |
| **Tier 1** | **Rule 5: Deduplication Check** | SHA256 checksum uniqueness, temporal segment 1D IoU $\le 0.30$ against previously published clips. | **STRICTLY FORBIDDEN (NON-OVERRIDABLE)**. Duplicate footage cannot be republished. |
| **Tier 1** | **Rule 6: Metadata & Disclaimer Completeness** | Valid title, SEO description, hashtags, tags, and mandatory Rockstar Games copyright disclaimer. | **STRICTLY FORBIDDEN (NON-OVERRIDABLE)**. Missing legal disclaimers cannot be bypassed. |
| **Tier 2** | **Rule 3: Semantic Status Validity** | VLM analysis status != `"FALLBACK"` (i.e., keyframes successfully evaluated by local VLM without timeout). | **REVIEWABLE EDITORIAL RULE (OVERRIDABLE)**. Human approval CAN review and approve fallback commentary. |
| **Tier 2** | **Rule 1: Engagement Score Threshold** | Composite engagement score $\ge 85.0$. | **REVIEWABLE EDITORIAL RULE (OVERRIDABLE)**. Human approval CAN approve borderline clips ($\ge 75.0$). |

#### Formal Evaluation Boolean Logic:
$$\text{Tier1Passed} = \text{Rule2}_{\text{Rights}} \land \text{Rule4}_{\text{Media}} \land \text{Rule5}_{\text{Dedupe}} \land \text{Rule6}_{\text{Metadata}}$$
$$\text{Tier2Passed} = \text{Rule1}_{\text{Engagement}} \land \text{Rule3}_{\text{Semantic}}$$
$$\text{Key1} = (\text{clip.approved\_for\_upload} == 1) \land (\text{clip.status} \ne \text{'rejected'})$$
$$\text{Key2} = \text{Tier1Passed} \land (\text{Tier2Passed} \lor \text{Key1})$$
$$\text{CanUpload} = \text{Key1} \land \text{Key2} \iff \text{Key1} \land \text{Tier1Passed}$$

#### Truth Table: Two-Key Gate Authorization Matrix:
| Tier 1 (Legal / Media Invariants) | Tier 2 (Editorial / Fallback Rules) | Key 1 (Human Approved) | Key 2 Evaluation | Final CanUpload Verdict | Rationale & Operational Behavior |
|---|---|---|---|---|---|
| **FAIL** (e.g. unverified source) | **PASS** | **TRUE** | **FAIL** | **FAIL-CLOSED (REJECTED)** | **Strict Block**: Human approval cannot override copyright or corrupted media. |
| **FAIL** (e.g. missing audio) | **FAIL** (fallback VLM) | **TRUE** | **FAIL** | **FAIL-CLOSED (REJECTED)** | **Strict Block**: Hardware / spec violations cannot be overridden. |
| **PASS** | **FAIL** (fallback VLM) | **FALSE** | **FAIL** | **FAIL-CLOSED (GATED)** | **Awaiting Review**: Unreviewed fallback commentary cannot auto-publish. |
| **PASS** | **FAIL** (fallback VLM) | **TRUE** | **PASS** | **AUTHORIZED (PUBLISH)** | **Approved Fallback**: Human verified the clip; fallback commentary permitted. |
| **PASS** | **PASS** | **FALSE** | **PASS** | **AWAITING APPROVAL** | **Two-Key Enforcement**: Quality passed, but upload requires explicit human key. |
| **PASS** | **PASS** | **TRUE** | **PASS** | **AUTHORIZED (PUBLISH)** | **Full Compliance**: Both human approval and full automated policy satisfied. |

```
Upload Requested for Clip
           │
           ▼
┌────────────────────────────────────────────────────────┐
│           Key 1: Human Approval Verification           │
│   Is clip.approved_for_upload == 1 and not rejected?   │
└──────────────────────────┬─────────────────────────────┘
                           │
                 [Key 1 Verified?]
                 ├───────── NO ─────────► [FAIL-CLOSED: Reject Upload]
                YES
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│     Key 2: Tier 1 Legal & Media Invariant Gate         │
│  - Rule 2: Source Rights Verified (NON-OVERRIDABLE)    │
│  - Rule 4: Video Spec Valid (1080x1920, 15-60s, audio) │
│  - Rule 5: Duplicate Check Passed (NON-OVERRIDABLE)    │
│  - Rule 6: Complete Metadata & Disclaimer Present      │
└──────────────────────────┬─────────────────────────────┘
                           │
               [All Tier 1 Passed?]
                 ├───────── NO ─────────► [FAIL-CLOSED: Reject Upload (Zero Bypass)]
                YES
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│     Key 2: Tier 2 Reviewable Editorial Evaluation      │
│  - Rule 1: Engagement Score >= 85.0                    │
│  - Rule 3: Semantic Status != 'FALLBACK'               │
└──────────────────────────┬─────────────────────────────┘
                           │
           [Tier 2 Passed OR Key 1 Overridden?]
                 ├───────── NO ─────────► [FAIL-CLOSED: Reject Upload]
                YES
                 │
                 ▼
     [Upload Authorized to Proceed]
```

#### Non-Overridable Invariant Guarantee:
**Human approval CANNOT override missing source rights, media corruption, or missing legal disclaimers.** Even if an operator marks a clip as approved, if `sources.permission_verified != 1` or valid license evidence is absent, Tier 1 strictly fails, and `upload_short()` terminates immediately with an unrecoverable error. Conversely, human approval **CAN override Tier 2 editorial rules**, enabling authorized publication of fallback commentary or human-curated highlights.

---

### 8.3 Decoupling Approval from Upload & Real-Time Re-Evaluation
- **Decoupled Workflow**:
  - `POST /api/clips/{id}/approve` or `cli.py approve` validates baseline clip integrity and transitions status to `approved`.
  - `POST /api/clips/{id}/upload` or `cli.py upload` triggers the upload process.
- **Upload-Time Re-Evaluation**:
  - Immediately before initiating YouTube network transmission, `youtube_uploader.py` re-probes the physical media file on disk via ffprobe and re-runs `publishing_policy.evaluate()`.
  - If the file was tampered with, moved, corrupted, or if source permission was revoked between approval and upload, the upload fails closed.

---

### 8.4 Tri-Simulation Settings & Fail-Gracefully Guarantees
Simulation behavior is governed by three decoupled, independent configuration flags in `config.py`:
1. `YOUTUBE_UPLOAD_SIMULATION: bool = True` (controls YouTube Shorts publishing).
2. `LIVESTREAM_DISCOVERY_MOCK: bool = True` (controls YouTube Data API v3 live search).
3. `FOOTAGE_ACQUISITION_SIMULATION: bool = True` (controls livestream video ingestion and chunk generation).

#### Operational Semantics:
- **Upload Simulation (`YOUTUBE_UPLOAD_SIMULATION = True`)**:
  - `youtube_uploader.py` validates the complete two-key gate, executes all media integrity and metadata checks, and records a simulated record in `publishing_history` with video ID `sim_{clip_id}_{timestamp}` without dispatching network calls to Google servers.
  - A live upload requires explicit command-line override (`--no-simulate` / `YOUTUBE_UPLOAD_SIMULATION=0`) AND an explicit confirmation environment variable `YOUTUBE_LIVE_UPLOAD_CONFIRMED=1`.
- **Graceful Failure Invariant (No Silent Synthetic Fallbacks)**:
  - If an operator sets any simulation flag to `False` (intending real production execution), the system **strictly disables synthetic generation**.
  - If required OAuth tokens, client secrets, API keys, or stream keys are missing or invalid, the platform **immediately halts with an explicit, actionable error** (e.g. `AuthenticationError: Live YouTube upload requested, but valid OAuth token not found in YOUTUBE_TOKEN_JSON or token.json. Run 'python cli.py auth' or enable YOUTUBE_UPLOAD_SIMULATION=1.`).
  - The system **never silently falls back to synthetic results** during production execution.

---

### 8.5 Credential Secrecy, `.gitignore` Hardening & Zero-Sibling-Traversal Guarantee
1. **`.gitignore` Hardening**:
   - The repository `.gitignore` is hardened with explicit patterns to ensure zero accidental credential leakage:
     ```gitignore
     # YouTube OAuth & Stream Ingestion Credentials
     token.json
     youtube_token.json
     client_secrets.json
     *.pickle
     *.token
     *.key
     *.secret
     ```
2. **Environment Variable Precedence & Zero Plaintext DB Secrets**:
   - Stream keys are strictly referenced via `secret_ref` strings (`"ENV:VAR_NAME"` or `"VAULT:KEY_ID"`), never stored as raw plain text in SQLite.
   - The YouTube credential loader prefers environment variables over filesystem tokens:
     - `YOUTUBE_CLIENT_SECRET_JSON`: Raw JSON string containing client secrets.
     - `YOUTUBE_TOKEN_JSON`: Raw JSON string containing authorized user OAuth credentials.
   - Filesystem lookup is only used as a secondary fallback if environment variables are unset.
3. **Complete Elimination of Sibling Workspace Traversal**:
   - Delete all references to `Path(config.PROJECT_ROOT).parent / "youtube-agent-skill"` across `youtube_uploader.py`, `source_discovery.py`, and all test suites.
   - The project is fully self-contained. It strictly forbids discovering or loading credentials from adjacent directories.

---

## 9. Database Migrations & Schema Extensions

### 9.1 SQLite Engine Hardening: WAL Mode & Concurrency Configuration
To allow concurrent reads and writes from multiple stream monitors and background workers, `database/db.py` is configured with:

```python
@contextmanager
def get_connection(self):
    """Context manager with WAL mode and 30-second busy timeout."""
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
```

---

### 9.2 Versioned Migration Runner Architecture
Dynamic column alterations in `db.py:init_db()` are replaced by a robust, versioned migration runner:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The runner executes ordered SQL migration scripts (`database/migrations/001_initial_schema.sql`, `002_priority_5_tables.sql`, etc.) inside atomic database transactions.

---

### 9.3 Comprehensive Database Schema Architecture: Existing vs. New Tables (R1–R12)

The database architecture maintains strict backward compatibility with existing Priority 1–4 tables while introducing specialized tables to support multi-stream discovery, rights tracking, chunk buffering, event detection, job queuing, and quota accounting.

#### 1. Existing Tables (Preserved & Reused from Priority 1–4):
- **`sources`**: Ingested static video sources, licenses, and base permissions.
- **`gameplay_files`**: Physical file metadata (paths, resolutions, durations, FPS, SHA256 hashes).
- **`scenes`**: Scene cut boundaries, visual deltas, and audio RMS energies.
- **`clips`**: Generated highlight clips, engagement metrics, semantic ratings, and final rendering paths.
- **`metadata`**: AI-generated titles, descriptions, hashtags, tags, and Rockstar Games legal disclaimers.
- **`publishing_history`**: Audit trail of uploaded YouTube Shorts, video IDs, privacy statuses, and API logs.

---

#### 2. Comprehensive DDL for New Priority 5 Tables (R1 through R12):

```sql
-- ============================================================================
-- 1. Schema Migrations (Versioned DDL Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. Discovered Streams (Public Metadata Only - Separated from Acquisition)
-- ============================================================================
CREATE TABLE IF NOT EXISTS discovered_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_video_id TEXT NOT NULL UNIQUE,
    channel_id TEXT NOT NULL,
    channel_title TEXT NOT NULL,
    title TEXT NOT NULL,
    thumbnail_url TEXT,
    viewer_count INTEGER,                    -- NULL if hidden, private, or pre-live (never default 0)
    stream_start_time TIMESTAMP,
    ended_at TIMESTAMP,                      -- Timestamp stream concluded (reconciled by discovery)
    is_live INTEGER DEFAULT 1,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_polled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    has_authorized_source INTEGER DEFAULT 0  -- 0 = Metadata Only (Unlicensed); 1 = Authorized
);

-- Backward-compatibility view
CREATE VIEW IF NOT EXISTS livestreams AS 
SELECT id, stream_video_id, channel_id, channel_title, title, viewer_count, is_live, has_authorized_source, discovered_at 
FROM discovered_streams;

-- ============================================================================
-- 3. Authorized Footage Sources (Legal Permissions & Credential References)
-- ============================================================================
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

-- ============================================================================
-- 4. Source Access Records (Immutable Ingestion Audit Trail)
-- ============================================================================
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

-- ============================================================================
-- 5. Monitoring Sessions (Bounded Rolling Chunk Buffer Tracking)
-- ============================================================================
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

-- ============================================================================
-- 6. Stream Health Telemetry
-- ============================================================================
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

-- ============================================================================
-- 7. Detected Events (Stage 1 & Stage 2 Event Log per Chunk)
-- ============================================================================
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

-- ============================================================================
-- 8. Highlight Candidates (Extracted Highlights with Pinned Chunk References)
-- ============================================================================
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

-- ============================================================================
-- 9. Publishing Queue (Two-Key Gated Review & Dispatch Pipeline)
-- ============================================================================
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

-- ============================================================================
-- 10. Persistent Background Processing Jobs (Task Queue & Recovery)
-- ============================================================================
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

-- ============================================================================
-- 11. YouTube API Quota Usage Accounting (Pacific Time Midnight Reset)
-- ============================================================================
CREATE TABLE IF NOT EXISTS youtube_api_quota_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,                  -- 'search.list', 'videos.list', 'videos.insert'
    units_consumed INTEGER NOT NULL,         -- 100 for search, 1 for videos.list, 1600 for upload
    caller_context TEXT NOT NULL,            -- 'background_discovery', 'manual_search', 'reconciliation', 'upload'
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quota_date_pt TEXT NOT NULL              -- Date in 'YYYY-MM-DD' under America/Los_Angeles timezone
);

-- ============================================================================
-- Comprehensive Performance Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_discovered_streams_live ON discovered_streams(is_live, has_authorized_source);
CREATE INDEX IF NOT EXISTS idx_monitoring_sessions_status ON monitoring_sessions(session_status);
CREATE INDEX IF NOT EXISTS idx_stream_health_session ON stream_health(session_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_detected_events_session ON detected_events(session_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_highlight_candidates_status ON highlight_candidates(status, composite_engagement_score);
CREATE INDEX IF NOT EXISTS idx_publishing_queue_status ON publishing_queue(review_status, key1_human_approved);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_queue ON processing_jobs(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_youtube_quota_date ON youtube_api_quota_usage(quota_date_pt, recorded_at);
```

---

## 10. Application Restart Recovery & Persistence

### 10.1 Persistent SQLite Task Queue Architecture
In `modules/job_queue.py`, background work is abstracted into persistent database tasks processed by a bounded worker pool (`max_concurrent_workers = 2`).
- Jobs are enqueued into `processing_jobs` with payload parameters (e.g., `{"clip_id": 42, "template": "cinematic_hype"}`).
- Workers acquire jobs atomically using SQLite transactions:
  ```sql
  UPDATE processing_jobs
  SET status = 'running', worker_id = :worker_id, started_at = CURRENT_TIMESTAMP
  WHERE id = (
      SELECT id FROM processing_jobs
      WHERE status = 'queued'
      ORDER BY priority ASC, created_at ASC
      LIMIT 1
  );
  ```

---

### 10.2 The ApplicationRecoveryService Startup Reconciler
Implemented in `modules/recovery_service.py`, this service runs unconditionally whenever `web_app.py`, `app.py`, or `cli.py` initializes.

#### Reconciliation Rules:
1. **Interrupted Processing Jobs**:
   - Any job found in status `running` on startup was interrupted by process termination.
   - If `retry_count < max_retries`, reset status to `queued`, increment `retry_count`, and log recovery.
   - If `retry_count >= max_retries`, set status to `failed` with error `"Interrupted by abnormal application restart; max retries exceeded."`
2. **Active Monitoring Sessions**:
   - Any session in status `active` is inspected.
   - The service tests whether the stream connection is alive.
   - If dead, the session status is updated to `abrupted`, `stopped_at = CURRENT_TIMESTAMP`.
3. **Orphan Chunk File Purging**:
   - Scans `output/buffer/` and deletes chunk directories corresponding to closed or abrupted sessions.
   - Scans `output/candidates/` and removes intermediate files not associated with any record in `clips`.

---

### 10.3 Crash Recovery State Machine

```
Process Crash / Restart Detected
               │
               ▼
┌────────────────────────────────────────────────────────┐
│     Execute ApplicationRecoveryService.reconcile()     │
└──────────────────────────────┬─────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
[Inspect processing_jobs]                   [Inspect monitoring_sessions]
       │                                               │
Status == 'running'?                        Status == 'active'?
 ├── retry < max: Re-queue                   ├── Stream still live: Resume buffer
 └── retry >= max: Mark 'failed'             └── Stream offline: Mark 'abrupted'
                                                       │
                                                       ▼
                                            [Purge Orphan Chunks & Temp Files]
```

---

## 11. Dashboard & CLI Enhancements

### 11.1 Web Application Architecture Upgrades (`web_app.py`)
1. **Asynchronous API Conversion**:
   - `POST /api/upload` no longer runs pipeline processing synchronously. It saves the uploaded file, inserts a `gameplay_files` record, enqueues a `pipeline_process` task into `processing_jobs`, and returns HTTP 202 Accepted with a `job_id`.
   - Adds polling endpoint `GET /api/jobs/{job_id}` returning job status (`queued`, `running`, `completed`, `failed`) and progress percentage.
2. **New Dashboard Views**:
   - **Discovered Streams Panel**: Lists live streams from `discovered_streams` with viewer counts, thumbnail, and authorization status badge ("Authorized Feed" vs "Metadata Only — Unlicensed").
   - **Active Sessions Monitor**: Real-time cards displaying session duration, total chunks captured, detected highlights count, and stream health status.
   - **Queue & System Health Gauge**: Real-time display of queue depth, active worker threads, CPU load, and disk utilization against the 10 GB threshold.

---

### 11.2 Streamlit Dashboard Upgrades (`app.py`)
- New Tab: **Live Stream Discovery**:
  - Button: "Poll Active GTA 6 Streams".
  - Data table showing discovered streams.
  - Action buttons: "Grant Authorization Evidence" and "Start Bounded Monitoring".
- New Tab: **System Health & Queue**:
  - Displays table of active background jobs in `processing_jobs`.
  - Manual triggers for "Run Garbage Collection" and "Run Startup Reconciler".

---

### 11.3 CLI Command Extensions (`cli.py`)
Four new commands are added to `cli.py`:

```bash
# 1. Discover active livestreams via YouTube Data API
python cli.py discover-streams --query "GTA 6" --limit 10

# 2. Manage livestream monitoring sessions
python cli.py monitor start <stream_video_id> [--max-chunks 5] [--chunk-duration 12]
python cli.py monitor stop <session_id>
python cli.py monitor list

# 3. Start background persistent queue worker daemon
python cli.py worker start [--concurrency 2]

# 4. Execute manual startup state reconciliation and garbage collection
python cli.py recover [--purge-orphans]
```

---

## 12. Comprehensive 25-Point Automated Test Suite Plan

### 12.1 Test Suite Organization & Mocking Strategy
The test suite resides in `tests/test_priority_5_comprehensive.py`. It uses synthetic test fixtures (via FFmpeg `lavfi`) and strictly mocked YouTube API responses to ensure 100% deterministic execution without network dependencies, external API calls, or quota consumption.

---

### 12.2 Detailed Specifications for Test Cases 1 through 25

| # | Test Name | Target Module | Test Scenario & Verification Assertions |
|---|---|---|---|
| **1** | `test_youtube_discovery_search_success` | `livestream_discovery.py` | Mock YouTube Data API Step 1 search and Step 2 `videos.list` response returning 3 active GTA 6 streams. Assert `discover_active_streams()` parses video ID, channel ID, viewer count (`concurrentViewers`), and sets `has_authorized_source = False`. |
| **2** | `test_youtube_discovery_quota_caching` | `livestream_discovery.py` | Call discovery twice within TTL window (300s). Assert second call returns cached DB records with zero additional network/API invocations. |
| **3** | `test_youtube_discovery_quota_exceeded_backoff` | `livestream_discovery.py` | Mock HTTP 403 `quotaExceeded`. Assert discovery catches exception gracefully, sets circuit-breaker, logs warning, and enters backoff without crashing. |
| **4** | `test_search_omission_vs_stream_offline_reconciliation` | `livestream_discovery.py` | Seed DB with active stream. Mock `search.list` omitting the stream (e.g. dropped out of top 10), but mock targeted `videos.list` returning `liveBroadcastContent = 'live'`. Assert stream is **NOT marked offline** and monitoring session remains active. |
| **5** | `test_pacific_time_quota_reset_boundary` | `livestream_discovery.py` | Record 4,800 units used on date $D$. Simulate clock advancing past 00:00:00 America/Los_Angeles (PT). Assert daily quota counter strictly resets to 0 units for the new Pacific Time calendar day. |
| **6** | `test_unauthorized_footage_rejection` | `authorized_source_adapter.py` | Attempt to acquire video chunk for a stream whose channel has no verified record in `authorized_footage_sources`. Assert `UnauthorizedFootageError` is raised. |
| **7** | `test_authorized_adapter_chunk_acquisition` | `authorized_source_adapter.py` | Register valid source evidence (`CREATIVE_COMMONS_VERIFIED`). Ingest synthetic 12s chunk via adapter. Assert `ChunkMetadata` returned with valid duration, fps, and audio. |
| **8** | `test_discovery_does_not_grant_acquisition_rights` | `livestream_discovery.py` | Discover a public stream and sync to DB. Verify `discovered_streams.has_authorized_source == 0`. Verify adapter refuses capture until explicit permission is bound. |
| **9** | `test_credential_secrecy_and_no_raw_keys_in_db` | `authorized_source_adapter.py` | Insert authorized source with `stream_key_secret_ref = 'ENV:TEST_KEY'`. Assert database contains only the reference string, zero plain text secrets are stored, and spawned FFmpeg processes pass secrets via stdin, not CLI arguments. |
| **10** | `test_independent_simulation_mode_flags` | `config.py`, `pipeline.py` | Toggle combinations of `YOUTUBE_UPLOAD_SIMULATION`, `LIVESTREAM_DISCOVERY_MOCK`, and `FOOTAGE_ACQUISITION_SIMULATION`. Assert each setting behaves independently without state bleed, and disabling a flag without real credentials raises an actionable error instead of falling back to mocks. |
| **11** | `test_bounded_ring_buffer_rotation` | `livestream_monitor.py` | Ingest 8 consecutive 12s chunks into a monitor configured with `max_chunks = 5`. Assert that only the 5 most recent chunks remain on disk, and chunks 1–3 are deleted. |
| **12** | `test_pinned_buffer_retention_under_rotation` | `livestream_monitor.py` | Flag an event in Chunk 3, causing Chunks 1, 2, 3, 4, 5 to be marked `is_pinned = True`. Ingest Chunks 6 through 12. Assert that pinned Chunks 1–5 are preserved on disk and immune from FIFO deletion until unpinned. |
| **13** | `test_disk_quota_enforcement` | `livestream_monitor.py` | Mock disk storage check exceeding `max_disk_usage_gb` (10 GB). Assert garbage collection triggers, unapproved/buffer chunks are purged, and session remains stable. |
| **14** | `test_ffmpeg_thread_clamping` | `clip_generator.py`, `video_editor.py` | Inspect FFmpeg execution command lines across clipping and video editing. Assert `-threads 4` is present and `-threads 0` is completely absent. |
| **15** | `test_stage1_fast_heuristic_filter_rejection` | `scene_detector.py`, `video_analyzer.py` | Feed static low-motion synthetic chunk ($S_{\text{heuristic}} < 65.0$). Assert filter rejects chunk in $< 1.5$ seconds without invoking VLM analyzer. |
| **16** | `test_stage1_fast_heuristic_filter_acceptance` | `scene_detector.py`, `video_analyzer.py` | Feed high-motion high-audio synthetic chunk ($S_{\text{heuristic}} \ge 65.0$). Assert chunk is accepted and forwarded to Stage 2 within 2.0 seconds. |
| **17** | `test_stage2_vlm_keyframe_extraction_monotonicity` | `semantic_analyzer.py` | Pass candidate chunk to Stage 2. Assert exactly 3 keyframes extracted with strictly monotonic timestamps: $t_{\text{start}} \le t_1 < t_2 < t_3 \le t_{\text{end}}$. |
| **18** | `test_temporal_iou_nms_deduplication` | `highlight_ranker.py` | Supply two overlapping candidate events ($[10.0, 35.0]$ and $[20.0, 45.0]$, $\text{IoU} = 0.60$). Assert NMS merges them into a single coherent highlight. |
| **19** | `test_conditional_fps_60fps_preservation` | `video_editor.py` | Feed `benchmark_gta6_gameplay_1080p60.mp4` (60.0 FPS). Render vertical short. Probe output with ffprobe; assert rendered video is exactly 60.0 FPS. |
| **20** | `test_conditional_fps_30fps_native` | `video_editor.py` | Feed 30.0 FPS synthetic video. Render vertical short. Probe output with ffprobe; assert rendered video is 30.0 FPS without artificial frame duplication. |
| **21** | `test_action_fast_zoompan_dynamic_fps_fix` | `video_editor.py` | Render clip using `action_fast` template with 60 FPS input. Assert filtergraph specifies `:fps=60` and output is 60 FPS (confirming fix of hardcoded `:fps=30`). |
| **22** | `test_audio_ducking_and_loudness_compliance` | `audio_processor.py` | Mix gameplay audio with voiceover and BGM. Probe rendered audio: assert gameplay is ducked during voiceover and EBU R128 integrated loudness is within $[-16.0, -12.0]$ LUFS. |
| **23** | `test_two_key_publishing_gate_enforcement` | `youtube_uploader.py` | (1) Attempt upload on clip with `is_approved = True` but missing source permission (`permission_verified = 0`); assert upload is strictly REJECTED (Tier 1 invariant non-overridable). (2) Attempt upload on clip with `permission_verified = 1`, valid media specs, but `semantic_status = 'FALLBACK'`; assert rejected when unapproved, but authorized when `is_approved = True` (Tier 2 reviewable editorial override). |
| **24** | `test_upload_time_policy_reevaluation` | `youtube_uploader.py` | Approve clip, then corrupt or delete local video file before upload. Assert upload re-evaluates policy at upload time and aborts with clear error. |
| **25** | `test_restart_recovery_reconciliation` | `recovery_service.py` | Seed DB with 1 `running` job, 1 `active` dead session, and 3 orphan chunks. Execute `ApplicationRecoveryService.reconcile()`. Assert job is re-queued/failed, session is marked `abrupted`, and orphan files are purged. |

---

## 13. Risks, Tradeoffs & Mitigations

### 13.1 Technical Risk Matrix

| Risk Event | Severity | Probability | Impact Description | Architectural Mitigation Strategy |
|---|---|---|---|---|
| **YouTube Data API Quota Depletion** | High | Medium | Repeated polling exhausts 10,000 daily quota limit, halting discovery. | Mandate single-page polling (`max_pages = 1`, 96 calls/day = 9,600 units/day); reserve 400 units/day buffer for manual queries; exponential backoff on 5xx; circuit-breaker on 403; SQLite cache with 300s TTL; offline simulation mode. |
| **Processing Lag on Live Streams** | High | Medium | If VLM or video render takes longer than chunk duration (12s), buffer queue grows unbounded. | Asynchronous decoupling: 12s stream monitor loop executes Stage 1 CV/audio in $<1.5$s, enqueues Stage 2 VLM tasks into `processing_jobs` table, and returns immediately without blocking. Workers process VLM independently. |
| **Workstation CPU/Memory Saturation** | Critical | Low | FFmpeg running multiple unconstrained encodes locks user machine. | Hard limit `-threads 4` in all FFmpeg calls; max 3 concurrent stream sessions; max 2 background video rendering jobs; optional NVENC GPU acceleration. |
| **Disk Exhaustion from Continuous Video** | Critical | Medium | Multi-hour livestreams generate hundreds of GBs of video chunks. | Bounded 5-chunk rolling ring buffer ($\approx 15$ MB/stream); Candidate Admission Governor (max 1 clip/60s, dynamic threshold raising, storage-aware shedding); automated 10 GB disk cap with GC routine. |
| **SQLite Concurrency Deadlocks** | High | Medium | Multiple stream threads and worker processes write to DB simultaneously. | Migrate SQLite to `PRAGMA journal_mode = WAL;` and set `PRAGMA busy_timeout = 30000;` (30s retry window). |
| **Copyright Infringement / Content Strikes** | Critical | Low | Accidental clipping and publishing of unauthorized third-party livestreams. | Absolute decoupling of discovery from acquisition; `AuthorizedSourceAdapter` raises `UnauthorizedFootageError`; fail-closed two-key publishing gate. |
| **VLM Hallucination in Spoken Commentary** | Medium | Low | Vision model describes events not occurring in GTA 6 gameplay. | Factual fallback activates on low confidence; commentary templates grounded strictly in detected event tags; human review required before publishing. |

---

### 13.2 Legal, Policy & Operational Safeguards
1. **Terms of Service Compliance**:
   - The platform strictly adheres to the YouTube API Services Terms of Service. Metadata queried from the YouTube Data API is used solely for indexing and display; it is never sold or used to circumvent YouTube access controls.
2. **Fair Use & Copyright Policy**:
   - All footage acquisition requires explicit authorization (creator agreement, user-owned recording, or official Rockstar Games press kit).
   - In accordance with Rockstar Games policy, all generated metadata automatically appends the non-commercial disclaimer: *"Grand Theft Auto VI and GTA 6 are trademarks of Rockstar Games, Take-Two Interactive. Gameplay captured under fair use / authorized creator program."*
3. **Simulation Mode Default**:
   - The platform defaults to `simulate_upload = True`. No video can be published to a live YouTube channel without manual, deliberate operator intervention disabling simulation mode and confirming live credentials.

---

## 14. Roadmap for Subsequent Phases (R2–R12)

### 14.1 Execution Phases & Dependency Graph

```
[Phase 1: Repository Audit & Implementation Plan (R1)] ◄── CURRENT DELIVERABLE (STOP FOR APPROVAL)
                         │
                         ▼ (Requires Explicit User Approval)
[Phase 2: Database Schema Migrations & WAL Engine (R2)]
                         │
                         ├────────────────────────────────────────┐
                         ▼                                        ▼
[Phase 3: YouTube Discovery Service (R3)]     [Phase 4: Authorized Source Adapter (R4)]
                         │                                        │
                         └───────────────────┬────────────────────┘
                                             ▼
                        [Phase 5: Bounded Livestream Monitor (R5)]
                                             │
                                             ▼
                        [Phase 6: Two-Stage Event Detector (R6)]
                                             │
                                             ▼
                        [Phase 7: Conditional FPS & Video Editor (R7)]
                                             │
                                             ▼
                        [Phase 8: Audio Mixing & Loudness Norm (R8)]
                                             │
                                             ▼
                        [Phase 9: Fail-Closed Security & Hardening (R9)]
                                             │
                                             ▼
                        [Phase 10: Persistent Queue & Recovery Service (R10)]
                                             │
                                             ▼
                        [Phase 11: Dashboard UI & CLI Enhancements (R11)]
                                             │
                                             ▼
                        [Phase 12: 20-Point Test Suite & Benchmark Validation (R12)]
```

---

### 14.2 Detailed Milestone Deliverables (M2 through M10)

#### Milestone M2: Foundation & Data Architecture (Phases 2 & 4)
- **Scope**:
  - Implement SQLite WAL mode and connection timeout in `database/db.py`.
  - Create versioned migration runner and apply DDL for 5 new tables (`discovered_streams`, `authorized_footage_sources`, `monitoring_sessions`, `stream_health`, `processing_jobs`).
  - Implement `modules/authorized_source_adapter.py` with `AuthorizedSourceAdapter` interface and concrete implementations.
- **Verification**: Database migration unit tests pass; `UnauthorizedFootageError` reliably raised on unauthorized streams.

#### Milestone M3: Livestream Discovery & Ingestion Engine (Phases 3 & 5)
- **Scope**:
  - Implement `modules/livestream_discovery.py` with YouTube Data API search, caching, and quota management.
  - Implement `modules/livestream_monitor.py` with bounded rolling ring buffer (10–15s chunks, max 5 chunks retained).
  - Implement resource limits and background garbage collection in `config.py`.
- **Verification**: Mocked YouTube discovery returns parsed streams; ring buffer strictly deletes chunks beyond buffer length.

#### Milestone M4: Low-Latency Event Detection & Ranking (Phase 6)
- **Scope**:
  - Adapt `modules/scene_detector.py` and `modules/video_analyzer.py` for chunk-level evaluation.
  - Implement Stage 1 CV/audio fast filter ($< 1.5$s execution time).
  - Implement Stage 2 3-keyframe VLM extraction with factual fallback.
  - Implement temporal IoU Non-Maximum Suppression in `modules/highlight_ranker.py`.
- **Verification**: Fast filter rejects low-action chunks; keyframe extraction produces strictly monotonic timestamps; NMS merges overlapping events.

#### Milestone M5: Media Pipeline & Conditional Frame Rate (Phases 7 & 8)
- **Scope**:
  - Implement `probe_source_fps()` and `determine_target_fps()`.
  - Update `clip_generator.py` and `video_editor.py` to preserve 60 FPS when source $\ge 59$ FPS and natively support 30 FPS.
  - Fix hardcoded `:fps=30` in `action_fast` zoompan filter.
  - Implement BGM track mixing and EBU R128 (-14 LUFS) loudness normalization in `modules/audio_processor.py`.
  - Replace `-threads 0` with `-threads 4` in all FFmpeg calls.
- **Verification**: `benchmark_gta6_gameplay_1080p60.mp4` renders to vertical short at verified 60.0 FPS; audio conforms to -14 LUFS.

#### Milestone M6: Fail-Closed Security & Credential Hardening (Phase 9)
- **Scope**:
  - Eliminate the `is_approved` bypass in `modules/youtube_uploader.py:164–184`.
  - Enforce strict two-key gate (`human_approved == True` AND `publishing_policy.evaluate() == True`).
  - Ensure human approval can never override missing source rights.
  - Re-evaluate policy immediately at upload time.
  - Add `token.json` to `.gitignore`; support environment variables for OAuth tokens; remove sibling directory lookup.
- **Verification**: Security gate unit tests confirm that approving a clip with missing source rights strictly fails upload.

#### Milestone M7: Task Queue & Restart Recovery (Phase 10)
- **Scope**:
  - Implement `modules/job_queue.py` with persistent SQLite task queue and worker thread pool.
  - Implement `modules/recovery_service.py` (`ApplicationRecoveryService`) executing on application startup.
  - Reconcile interrupted `running` jobs, mark dead sessions `abrupted`, and purge orphan chunks.
- **Verification**: Simulated process crash test proves interrupted jobs are re-queued and orphan files are purged.

#### Milestone M8: Dashboard & CLI Upgrades (Phase 11)
- **Scope**:
  - Convert `POST /api/upload` in `web_app.py` to asynchronous background queue dispatch.
  - Add views for Discovered Streams (with Authorization badges), Active Monitoring Sessions, and Queue Health.
  - Update Streamlit `app.py` with live stream discovery and monitoring tabs.
  - Add CLI subcommands `discover-streams`, `monitor`, `worker`, and `recover` to `cli.py`.
- **Verification**: Web app and CLI trigger background tasks non-blockingly; UI renders live stream cards.

#### Milestone M9: Comprehensive 25-Point Test Suite (Phase 12)
- **Scope**:
  - Implement all 25 automated test cases in `tests/test_priority_5_comprehensive.py`.
  - Run full test suite covering existing 49 tests + 25 new tests (74 total tests).
  - Execute end-to-end 1080p 60FPS benchmark validation.
- **Verification**: 100% test pass rate across all 74 tests; benchmark renders 1080p60 vertical short within resource bounds.

---

### 14.3 Explicit User Approval Halting Protocol
In accordance with the prompt's instructions and project governance:
- **Phase 1 / R1 execution halts completely upon delivery of this document.**
- **No existing application code in `GTA_6` has been modified during this phase.**
- **Work on Phase 2 (Database Migrations & WAL Engine) and subsequent phases will begin only after the user explicitly reviews and approves this architectural specification.**
