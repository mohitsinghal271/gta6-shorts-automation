"""
GTA 6 AI Shorts Pipeline: Real 1080p 60FPS Benchmarking Runner
Measures end-to-end latency, resource utilization, and output quality on 1080p 60FPS gameplay.
"""

import time
import os
from pathlib import Path
from config import config
from database.db import db
from modules.pipeline import pipeline
from modules.publishing_policy import publishing_policy

def run_benchmark():
    video_file = Path('input') / 'benchmark_gta6_gameplay_1080p60.mp4'
    if not video_file.exists():
        print(f"Error: {video_file} not found. Please generate it first.")
        return

    print("=================================================================")
    print("GTA 6 AI SHORTS PIPELINE: REAL 1080P 60FPS BENCHMARK RUN")
    print("=================================================================")
    file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
    print(f"Input Video: {video_file} ({file_size_mb:.2f} MB)")

    t_start = time.time()

    # Execute complete production pipeline
    pipeline_res = pipeline.process_video_pipeline(
        video_path=video_file,
        language="hinglish",
        template_name="cinematic_hype",
        include_voiceover=True,
        top_clips=3
    )

    t_end = time.time()
    total_time = t_end - t_start

    print("\n---------------- PIPELINE EXECUTION SUMMARY ----------------")
    print(f"Total Pipeline Duration: {total_time:.2f} seconds")

    clips = pipeline_res.get("clips", [])
    print(f"Total Produced Shorts: {len(clips)}")

    for idx, clip_info in enumerate(clips, 1):
        final_path = clip_info.get("final_path")
        clip_id = clip_info.get("clip_id")
        score = clip_info.get("score")
        meta = db.get_metadata(clip_id)

        print(f"\n--- [SHORT #{idx}] Clip ID: {clip_id} ---")
        print(f"Engagement Score: {score}/100")
        print(f"Final Rendered Short: {final_path}")
        if final_path and os.path.exists(final_path):
            rendered_mb = os.path.getsize(final_path) / (1024 * 1024)
            print(f"Rendered Output Size: {rendered_mb:.2f} MB")

        # Evaluate Publishing Policy
        clip_row = db.get_clip(clip_id)
        eval_res = publishing_policy.evaluate(clip_row)
        print("Publishing Policy Evaluation:")
        print(f"  Can Auto-Publish: {eval_res.can_publish}")
        passed_count = sum(1 for v in eval_res.rules_passed.values() if v)
        print(f"  Rules Passed: {passed_count} / {len(eval_res.rules_passed)}")
        for r_name, r_pass in eval_res.rules_passed.items():
            status_str = "PASS" if r_pass else "BLOCKED"
            print(f"    - {r_name}: {status_str}")
        if eval_res.rejection_reasons:
            print(f"  Staging Details: {'; '.join(eval_res.rejection_reasons)}")

        if meta:
            print("Generated YouTube Packaging:")
            print(f"  Recommended Title: {meta.get('title_recommended')}")
            print(f"  Alt Title 1: {meta.get('title_alt_1')}")
            print(f"  Alt Title 2: {meta.get('title_alt_2')}")
            print(f"  Hashtags: {meta.get('hashtags')}")
            print(f"  Pinned Comment: {meta.get('pinned_comment')}")
            print(f"  Thumbnail Concept: {meta.get('thumbnail_concept')}")
    print("=================================================================")

if __name__ == "__main__":
    run_benchmark()
