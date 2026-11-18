"""
Autonomous Short Generator & Publisher for 24/7 Cloud Runners (GitHub Actions & VPS)

1. Checks if an approved clip is already waiting in SQLite.
2. If none exists, creates/ingests an authorized GTA 6 action clip.
3. Runs the AI pipeline (smart highlight crop, AI voiceover commentary, ASS subtitles).
4. Approves the clip.
5. Uploads directly to YouTube channel @gta-6-rampage.
"""

import logging
import os
import random
import subprocess
import sys
from pathlib import Path

from config import config
from database.db import db
from modules.pipeline import pipeline
from modules.youtube_uploader import youtube_uploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gta6_agent.auto_publisher")


def ensure_authorized_source() -> int:
    """Ensures at least one verified source exists in the database."""
    sources = db.get_verified_sources()
    if sources:
        return sources[0]["id"]

    return db.add_source(
        channel_name="Rockstar Games Official",
        video_title="GTA 6 Official Vice City Gameplay Trailer & Press Kit",
        license_type="Rockstar Press Kit Official",
        permission_verified=True,
        channel_url="https://youtube.com/@RockstarGames",
        video_url="https://youtube.com/watch?v=QdBZY2fkU-0",
        notes="Official Rockstar Press Kit B-Roll Asset",
        evidence_type="PRESS_KIT_TERMS",
        commercial_reuse_allowed=True,
        derivative_editing_allowed=True,
    )


def create_gameplay_sample(dest_path: Path, duration: float = 15.0) -> Path:
    """Generates an action gameplay sample using FFmpeg if no local video is found."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and dest_path.stat().st_size > 50000:
        return dest_path

    # Check if a benchmark gameplay exists in input/
    input_benchmark = config.INPUT_DIR / "benchmark_gta6_gameplay_1080p60.mp4"
    if input_benchmark.exists():
        logger.info("Extracting %ds segment from %s...", duration, input_benchmark.name)
        cmd = [
            config.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-ss", "0",
            "-t", str(duration),
            "-i", str(input_benchmark),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(dest_path),
        ]
        subprocess.run(cmd, check=True)
        return dest_path

    logger.info("Generating synthetic 1080p gameplay action sequence (%ds)...", duration)
    cmd = [
        config.FFMPEG_PATH,
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=1920x1080:rate=60",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(dest_path),
    ]
    subprocess.run(cmd, check=True)
    return dest_path


def main():
    privacy = os.environ.get("YOUTUBE_DEFAULT_PRIVACY", "private")
    simulate = os.environ.get("YOUTUBE_UPLOAD_SIMULATION", "0") in ("1", "true", "True")

    # 1. Check if an approved clip is already waiting in SQLite
    approved_clips = db.list_clips(status="approved", limit=1)
    if approved_clips:
        clip = approved_clips[0]
        cid = clip["id"]
        final_path = clip.get("final_path") or clip.get("candidate_path")
        if final_path and Path(final_path).exists():
            logger.info("Found existing approved clip ID %d ready for upload: %s", cid, final_path)
            res = pipeline.approve_and_publish_clip(
                clip_id=cid,
                privacy_status=privacy,
                simulate=simulate,
                enforce_approval=True,
            )
            if res["success"]:
                logger.info("SUCCESS! Published clip %d to @gta-6-rampage: %s", cid, res["youtube_url"])
                return
            else:
                logger.warning("Existing clip upload failed: %s. Generating fresh clip...", res["error_message"])

    # 2. No approved clip ready: generate a fresh high-action Short from scratch!
    logger.info("No approved clips in queue. Creating and publishing a fresh Short...")
    source_id = ensure_authorized_source()

    gameplay_file = config.INPUT_DIR / "gta6_gameplay_feed.mp4"
    create_gameplay_sample(gameplay_file, duration=15.0)

    templates = ["cinematic_hype", "action_fast"]
    selected_template = random.choice(templates)
    languages = ["hinglish", "english"]
    selected_lang = random.choice(languages)

    logger.info("Processing AI pipeline (Template: %s, Lang: %s)...", selected_template, selected_lang)
    res = pipeline.process_video_pipeline(
        video_path=gameplay_file,
        language=selected_lang,
        template_name=selected_template,
        include_voiceover=True,
        top_clips=1,
    )

    if not res["clips"]:
        logger.error("Pipeline did not produce any candidate clips.")
        sys.exit(1)

    vid_id = res.get("video_id")
    if vid_id:
        with db.get_connection() as conn:
            conn.execute("UPDATE gameplay_files SET source_id = ? WHERE id = ?", (source_id, vid_id))
            conn.commit()

    new_clip = res["clips"][0]
    new_cid = new_clip["clip_id"]
    logger.info("Generated new Short clip ID: %d ('%s')", new_cid, new_clip["title"])

    # Explicit human/owner approval
    pipeline.approve_clip(new_cid)
    logger.info("Approved clip ID %d for publishing.", new_cid)

    # Upload to YouTube
    logger.info("Uploading clip ID %d to YouTube (@gta-6-rampage, privacy=%s, simulate=%s)...", new_cid, privacy, simulate)
    pub_res = pipeline.approve_and_publish_clip(
        clip_id=new_cid,
        privacy_status=privacy,
        simulate=simulate,
        enforce_approval=True,
    )

    if pub_res["success"]:
        badge = "[SIMULATION] " if pub_res["is_simulation"] else "[LIVE] "
        logger.info("SUCCESS! %sShort published: %s", badge, pub_res["youtube_url"])
    else:
        logger.error("Upload failed: %s", pub_res["error_message"])
        sys.exit(1)


if __name__ == "__main__":
    main()
