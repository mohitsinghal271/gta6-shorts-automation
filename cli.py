"""
Command-Line Interface (CLI) for GTA 6 AI YouTube Shorts Automation Agent
Enables headless automation, cron schedules, and terminal workflows.
"""

import sys
import argparse
import logging
from pathlib import Path
from config import config
from database.db import db
from modules.gameplay_ingestion import ingestion_service
from modules.scene_detector import scene_detector
from modules.video_analyzer import video_analyzer
from modules.highlight_ranker import highlight_ranker
from modules.clip_generator import clip_generator
from modules.pipeline import pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gta6_agent.cli")


def cmd_scan(args):
    print(f"Scanning watched input folder: {config.INPUT_DIR}")
    results = ingestion_service.scan_and_ingest_input_folder()
    print(f"Ingested {len(results)} new gameplay videos.")
    for vid_id, meta in results:
        print(f"  - [ID {vid_id}] {meta.filename} ({meta.duration_seconds:.1f}s, {meta.width}x{meta.height})")


def cmd_ingest(args):
    p = Path(args.filepath)
    print(f"Ingesting video: {p}")
    vid_id, meta = ingestion_service.ingest_video_file(p)
    print(f"Success! Video ID: {vid_id}")
    print(f"  Duration: {meta.duration_seconds:.1f}s | Resolution: {meta.width}x{meta.height} | FPS: {meta.fps}")


def cmd_analyze(args):
    vid = db.get_gameplay_by_id(args.video_id)
    if not vid:
        print(f"Error: Video ID {args.video_id} not found.")
        sys.exit(1)

    print(f"Analyzing Video ID {args.video_id}: {vid['filename']}")
    scenes = scene_detector.process_and_save_scenes(
        video_id=args.video_id,
        video_path=Path(vid["filepath"]),
        duration=vid["duration_seconds"],
    )
    print(f"Detected {len(scenes)} scenes.")

    segments = video_analyzer.analyze_sliding_windows(
        video_path=Path(vid["filepath"]),
        duration=vid["duration_seconds"],
        scenes=scenes,
    )
    print(f"Analyzed {len(segments)} candidate segments.")
    ranked = highlight_ranker.rank_and_deduplicate(segments, top_n=args.top)
    print(f"\nTop {len(ranked)} Non-Redundant Highlights:")
    for idx, r in enumerate(ranked, 1):
        print(
            f"  {idx}. [{r.start_time:.1f}s - {r.end_time:.1f}s] Score: {r.composite_score:.1f} | Action: {r.action_intensity:.1f} | Tags: {r.tags}"
        )


def cmd_list_clips(args):
    clips = db.list_clips(status=args.status, limit=args.limit)
    print(f"Found {len(clips)} clips (Filter status={args.status or 'ALL'}):")
    for c in clips:
        meta = db.get_metadata(c["id"])
        title = meta["title_recommended"] if meta else "Untitled"
        print(
            f"  [ID {c['id']}] Score: {c['engagement_score']:.1f} | {c['status'].upper()} | {c['language']} | {title}"
        )
        print(f"       Path: {c['final_path'] or c['candidate_path']}")


def cmd_approve(args):
    c = db.get_clip_by_id(args.clip_id)
    if not c:
        print(f"Error: Clip ID {args.clip_id} not found.")
        sys.exit(1)
    pipeline.approve_clip(args.clip_id)
    print(f"Clip ID {args.clip_id} approved for YouTube publishing.")


def cmd_upload(args):
    c = db.get_clip_by_id(args.clip_id)
    if not c:
        print(f"Error: Clip ID {args.clip_id} not found.")
        sys.exit(1)
    if not c.get("approved_for_upload"):
        print(f"Error: Clip ID {args.clip_id} is not approved for upload.")
        print(f"Please run 'python cli.py approve {args.clip_id}' first.")
        sys.exit(1)

    # Determine simulation vs live mode
    simulate = False if getattr(args, "live", False) else args.simulate

    mode_label = "LIVE" if simulate is False else "SIMULATION"
    print(f"Publishing Clip ID {args.clip_id} to YouTube ({mode_label} mode, privacy={args.privacy})...")
    res = pipeline.approve_and_publish_clip(
        clip_id=args.clip_id,
        privacy_status=args.privacy,
        simulate=simulate,
        enforce_approval=True,
    )
    if res["success"]:
        sim_badge = "[SIMULATION] " if res["is_simulation"] else "[LIVE] "
        print(f"SUCCESS! {sim_badge}Video published: {res['youtube_url']}")
    else:
        print(f"FAILED to upload: {res['error_message']}")


def cmd_run_pipeline(args):
    p = Path(args.filepath)
    print(f"Running Full End-to-End Pipeline on {p.name} (Lang: {args.lang}, Template: {args.template})...")
    res = pipeline.process_video_pipeline(
        video_path=p,
        language=args.lang,
        template_name=args.template,
        include_voiceover=not args.no_voice,
        top_clips=args.top,
    )
    print(f"\nPipeline Complete! Generated {res['clips_generated']} shorts:")
    for c in res["clips"]:
        print(f"  - Clip ID {c['clip_id']}: '{c['title']}' (Score: {c['engagement_score']})")
        print(f"    File: {c['final_path']}")


def cmd_channel_status(args):
    print("Checking YouTube OAuth channel status...")
    try:
        from modules.youtube_uploader import youtube_uploader
        svc = youtube_uploader.get_authenticated_service()
        if svc:
            print("SUCCESS: YouTube OAuth 2.0 channel is connected and authenticated!")
            try:
                ch_res = svc.channels().list(mine=True, part="snippet").execute()
                items = ch_res.get("items", [])
                if items:
                    title = items[0]["snippet"].get("title", "Unknown")
                    custom_url = items[0]["snippet"].get("customUrl", "")
                    print(f"  Channel Title : {title}")
                    if custom_url:
                        print(f"  Channel Handle: {custom_url}")
            except Exception:
                pass
            token_path = getattr(youtube_uploader, "token_json_file", None) or config.youtube.token_pickle_file
            print(f"Token file: {token_path}")
            print(f"Default privacy: {config.youtube.default_privacy}")
            print(f"Simulation mode: {'ENABLED (dry run)' if config.youtube.simulate_upload else 'DISABLED (live uploads active)'}")
            print("Ready to publish Shorts to YouTube.")
        else:
            print("FAILED: Could not authenticate with YouTube API.")
    except Exception as e:
        print(f"ERROR: {e}")


def cmd_auth(args):
    """Interactive OAuth 2.0 authentication to connect a YouTube channel."""
    print("Initiating YouTube OAuth authentication...")
    try:
        from modules.youtube_uploader import SCOPES
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        secret_file = Path(config.PROJECT_ROOT) / "client_secrets.json"
        if not secret_file.exists():
            print(f"ERROR: client_secrets.json not found at {secret_file}")
            return
            
        print("Opening browser for OAuth sign-in...")
        print("Please log in with your YouTube Google account and select your channel.")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
        creds = flow.run_local_server(port=0)
        
        save_path = Path(config.PROJECT_ROOT) / "youtube_token.json"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
            
        print(f"\nSUCCESS: OAuth token saved to {save_path.name}!")
        print("Channel is now authenticated and ready for uploads.")
    except Exception as e:
        print(f"OAuth Authentication Error: {e}")


def cmd_stats(args):
    stats = db.get_dashboard_stats()
    print("=== GTA 6 AI Shorts Automation Stats ===")
    for k, v in stats.items():
        print(f"  {k.replace('_', ' ').title():<28}: {v}")


def cmd_discover_streams(args):
    from modules.livestream_discovery import LivestreamDiscoveryService
    service = LivestreamDiscoveryService()
    print(f"Searching for active livestreams with query '{args.query}' (limit {args.limit})...")
    streams = service.discover_active_streams(
        query=args.query,
        max_results=args.limit,
        is_manual=True,
        force_refresh=args.refresh,
    )
    print(f"\nDiscovered {len(streams)} active streams:")
    print(f"{'Stream ID':<20} {'Channel':<24} {'Viewers':<10} {'Authorized?':<12} {'Title'}")
    print("-" * 90)
    for s in streams:
        v_str = str(s.viewer_count) if s.viewer_count is not None else "N/A"
        auth_str = "YES" if s.has_authorized_source else "NO (Metadata)"
        print(f"{s.stream_video_id:<20} {s.channel_title[:22]:<24} {v_str:<10} {auth_str:<12} {s.title[:40]}")


def cmd_monitor(args):
    action = args.action
    if action == "list":
        sessions = db.get_active_monitoring_sessions()
        print(f"\n=== Active Monitoring Sessions ({len(sessions)}) ===")
        print(f"{'Session ID':<12} {'Stream Video ID':<20} {'Channel':<24} {'Chunks':<8} {'Highlights'}")
        print("-" * 80)
        for s in sessions:
            print(f"{s['id']:<12} {s['stream_video_id']:<20} {s['channel_title'][:22]:<24} {s['total_chunks_captured']:<8} {s['total_highlights_detected']}")
    elif action == "stop":
        db.update_monitoring_session_status(args.session_id, "stopped")
        print(f"Session {args.session_id} marked as stopped.")
    elif action == "start":
        from modules.livestream_monitor import LivestreamMonitor
        from modules.authorized_source_adapter import (
            CreatorAuthorizedStreamAdapter,
            SyntheticMockStreamAdapter,
            UnauthorizedFootageError,
        )
        stream_id = args.stream_video_id
        # Select adapter based on simulation flag
        if config.youtube.simulate_acquisition:
            adapter = SyntheticMockStreamAdapter()
        else:
            adapter = CreatorAuthorizedStreamAdapter()

        try:
            monitor = LivestreamMonitor(
                stream_video_id=stream_id,
                adapter=adapter,
                chunk_duration_sec=args.chunk_duration,
                max_buffer_chunks=args.max_chunks,
            )
            print(f"Starting LivestreamMonitor for {stream_id} (Session ID: {monitor.session_id})...")
            monitor.start()
            print("Press Ctrl+C to terminate monitoring.")
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nStopping monitor session...")
            monitor.stop()
            print("Session stopped.")
        except UnauthorizedFootageError as e:
            print(f"\n[LEGAL FIREWALL REJECTION] {e}")


def cmd_worker(args):
    from modules.job_queue import QueueWorkerPool
    pool = QueueWorkerPool(max_workers=args.concurrency)
    print(f"Starting persistent background worker daemon with {args.concurrency} threads...")
    pool.start()
    print("Worker pool running. Press Ctrl+C to shut down.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nShutting down worker pool...")
        pool.stop()
        print("Worker daemon stopped cleanly.")


def cmd_recover(args):
    from modules.recovery_service import recovery_service
    print("Executing startup state reconciliation and garbage collection...")
    res = recovery_service.reconcile(purge_orphans=args.purge_orphans)
    print("\n=== Application Recovery Summary ===")
    for k, v in res.items():
        print(f"  {k.replace('_', ' ').title():<26}: {v}")


def cmd_daemon(args):
    from daemon_service import GTA6AutonomousDaemon
    daemon = GTA6AutonomousDaemon(worker_concurrency=args.concurrency)
    print(f"Starting 24/7 Autonomous Daemon with {args.concurrency} workers...")
    daemon.start()


def main():
    parser = argparse.ArgumentParser(
        description="GTA 6 AI YouTube Shorts Automation Agent CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    subparsers.add_parser("scan", help="Scan input directory and ingest all videos")

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest a video file")
    p_ingest.add_argument("filepath", help="Path to gameplay video")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze video and rank highlights")
    p_analyze.add_argument("video_id", type=int, help="Database Video ID")
    p_analyze.add_argument("--top", type=int, default=5, help="Number of highlights")

    # list-clips
    p_list = subparsers.add_parser("list-clips", help="List generated clips")
    p_list.add_argument("--status", choices=["candidate", "pending_review", "approved", "published"])
    p_list.add_argument("--limit", type=int, default=20)

    # approve
    p_appr = subparsers.add_parser("approve", help="Approve clip for publishing")
    p_appr.add_argument("clip_id", type=int)

    # upload
    p_up = subparsers.add_parser("upload", help="Upload clip to YouTube")
    p_up.add_argument("clip_id", type=int)
    p_up.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    p_up.add_argument("--live", action="store_true", help="Perform real live upload to YouTube channel")
    p_up.add_argument("--simulate", action="store_true", default=None)

    # run-pipeline
    p_pipe = subparsers.add_parser("run-pipeline", help="Run full pipeline end-to-end on a video")
    p_pipe.add_argument("filepath", help="Path to video file")
    p_pipe.add_argument("--lang", choices=["hindi", "english", "hinglish"], default="hinglish")
    p_pipe.add_argument(
        "--template",
        choices=["cinematic_hype", "action_fast", "story_npc", "funny_moments"],
        default="cinematic_hype",
    )
    p_pipe.add_argument("--top", type=int, default=3)
    p_pipe.add_argument("--no-voice", action="store_true", help="Generate gameplay-only audio")

    # stats
    subparsers.add_parser("stats", help="Show system dashboard statistics")

    # channel-status
    subparsers.add_parser("channel-status", help="Check YouTube OAuth link and channel status")

    # auth
    subparsers.add_parser("auth", help="Authenticate or re-authenticate YouTube channel via OAuth 2.0")

    # discover-streams
    p_disc = subparsers.add_parser("discover-streams", help="Discover active GTA 6 livestreams")
    p_disc.add_argument("--query", default="GTA 6", help="Search query")
    p_disc.add_argument("--limit", type=int, default=10, help="Max results to fetch")
    p_disc.add_argument("--refresh", action="store_true", help="Bypass cache and force fresh API query")

    # monitor
    p_mon = subparsers.add_parser("monitor", help="Manage livestream monitoring sessions")
    mon_sub = p_mon.add_subparsers(dest="action", required=True)
    mon_start = mon_sub.add_parser("start", help="Start monitoring an authorized stream")
    mon_start.add_argument("stream_video_id", help="YouTube video ID of stream")
    mon_start.add_argument("--max-chunks", type=int, default=5, help="Rolling buffer chunk retention")
    mon_start.add_argument("--chunk-duration", type=float, default=12.0, help="Chunk duration in seconds")
    mon_sub.add_parser("list", help="List active monitoring sessions")
    mon_stop = mon_sub.add_parser("stop", help="Stop a monitoring session")
    mon_stop.add_argument("session_id", type=int, help="Session ID to terminate")

    # worker
    p_work = subparsers.add_parser("worker", help="Start background task queue worker daemon")
    p_work.add_argument("--concurrency", type=int, default=2, help="Number of worker threads")

    # recover
    p_rec = subparsers.add_parser("recover", help="Execute startup reconciliation and garbage collection")
    p_rec.add_argument("--purge-orphans", action="store_true", default=True, help="Purge orphan files")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run 24/7 master autonomous automation service")
    p_daemon.add_argument("--concurrency", type=int, default=2, help="Number of worker threads")

    args = parser.parse_args()

    commands = {
        "scan": cmd_scan,
        "ingest": cmd_ingest,
        "analyze": cmd_analyze,
        "list-clips": cmd_list_clips,
        "approve": cmd_approve,
        "upload": cmd_upload,
        "run-pipeline": cmd_run_pipeline,
        "stats": cmd_stats,
        "channel-status": cmd_channel_status,
        "auth": cmd_auth,
        "discover-streams": cmd_discover_streams,
        "monitor": cmd_monitor,
        "worker": cmd_worker,
        "recover": cmd_recover,
        "daemon": cmd_daemon,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(args)


if __name__ == "__main__":
    main()
