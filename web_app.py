"""
FastAPI Standalone Web Dashboard for GTA 6 AI YouTube Shorts Automation Agent
Provides full web UI with video player, approval controls, and REST API.
Run with: python web_app.py
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import config
from database.db import db
from modules.gameplay_ingestion import ingestion_service
from modules.pipeline import pipeline
from modules.recovery_service import recovery_service
from modules.livestream_discovery import LivestreamDiscoveryService

app = FastAPI(title="GTA 6 AI Shorts Automation Web Dashboard")

# On application startup, execute recovery reconciliation
@app.on_event("startup")
def on_startup():
    try:
        recovery_service.reconcile(purge_orphans=True)
    except Exception as e:
        pass

# Mount output directory for video streaming
app.mount("/media/output", StaticFiles(directory=str(config.OUTPUT_DIR)), name="media_output")


@app.get("/", response_class=HTMLResponse)
def index():
    stats = db.get_dashboard_stats()
    clips = db.list_clips(limit=25)
    history = db.get_publishing_history()

    # Generate Clip Cards HTML
    clip_cards_html = ""
    for c in clips:
        meta = db.get_metadata(c["id"])
        title = meta["title_recommended"] if meta else f"Clip #{c['id']}"
        desc = meta["description"][:160] + "..." if meta else ""
        rel_video_path = ""
        actual_path = c["final_path"] or c["candidate_path"]
        if actual_path and os.path.exists(actual_path):
            p = Path(actual_path)
            try:
                rel = p.relative_to(config.OUTPUT_DIR)
                rel_video_path = f"/media/output/{rel.as_posix()}"
            except Exception:
                rel_video_path = ""

        status_color = (
            "bg-yellow-500"
            if c["status"] == "pending_review"
            else "bg-green-500"
            if c["status"] in ["approved", "published"]
            else "bg-gray-500"
        )

        clip_cards_html += f"""
        <div class="bg-gray-800 rounded-xl overflow-hidden border border-gray-700 shadow-xl flex flex-col md:flex-row gap-4 p-4">
            <div class="w-full md:w-64 h-96 bg-black rounded-lg flex items-center justify-center overflow-hidden">
                {f'<video class="w-full h-full object-cover" controls src="{rel_video_path}"></video>' if rel_video_path else '<div class="text-gray-500">Video not found</div>'}
            </div>
            <div class="flex-1 flex flex-col justify-between">
                <div>
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs uppercase tracking-wider font-bold px-2 py-0.5 rounded text-white {status_color}">{c['status']}</span>
                        <span class="text-xs text-pink-400 font-semibold uppercase">{c['language']}</span>
                        <span class="text-xs text-gray-400 font-mono">ID: {c['id']} | {c['duration']}s</span>
                    </div>
                    <h3 class="text-lg font-bold text-white mb-1">{title}</h3>
                    <p class="text-xs text-gray-400 mb-3">{desc}</p>
                    
                    <div class="space-y-1.5 text-xs text-gray-300">
                        <div class="flex justify-between">
                            <span>Engagement Score:</span>
                            <span class="font-bold text-yellow-400">{c['engagement_score']} / 100</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2">
                            <div class="bg-yellow-400 h-2 rounded-full" style="width: {min(100, c['engagement_score'])}%"></div>
                        </div>
                        <div class="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-gray-700 text-center">
                            <div><span class="text-gray-400">Action:</span> <span class="font-semibold">{c['action_score']}%</span></div>
                            <div><span class="text-gray-400">Visual:</span> <span class="font-semibold">{c['visual_score']}%</span></div>
                            <div><span class="text-gray-400">Hook:</span> <span class="font-semibold">{c['hook_score']}%</span></div>
                        </div>
                    </div>
                </div>

                <div class="flex gap-2 mt-4 pt-3 border-t border-gray-700">
                    <form action="/api/clips/{c['id']}/approve" method="post" class="inline">
                        <button class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2 rounded-lg text-sm transition">
                            ✅ Approve
                        </button>
                    </form>
                    <form action="/api/clips/{c['id']}/upload" method="post" class="inline">
                        <button class="bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded-lg text-sm transition">
                            📤 Upload to YouTube
                        </button>
                    </form>
                </div>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GTA 6 AI Shorts Automation</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-100 min-h-screen font-sans">
        <!-- Header -->
        <header class="bg-gradient-to-r from-purple-900 via-pink-800 to-indigo-900 border-b border-pink-500/20 px-8 py-5">
            <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                        🌴 GTA 6 AI YouTube Shorts Studio
                    </h1>
                    <p class="text-xs text-pink-200 mt-1">Autonomous Multi-Modal Video Clipping, Localization & Publishing Agent</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        FFmpeg Ready
                    </span>
                    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-950 text-indigo-400 border border-indigo-800">
                        Edge-TTS / SAPI Active
                    </span>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-7xl mx-auto px-8 py-8 space-y-8">
            <!-- KPI Metric Cards -->
            <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <div class="text-xs text-gray-400">Total Videos Ingested</div>
                    <div class="text-2xl font-black text-white mt-1">{stats['total_videos_processed']}</div>
                </div>
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <div class="text-xs text-gray-400">Clips Extracted</div>
                    <div class="text-2xl font-black text-white mt-1">{stats['total_clips_generated']}</div>
                </div>
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <div class="text-xs text-gray-400">Pending Review</div>
                    <div class="text-2xl font-black text-yellow-400 mt-1">{stats['pending_review']}</div>
                </div>
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <div class="text-xs text-gray-400">Approved</div>
                    <div class="text-2xl font-black text-emerald-400 mt-1">{stats['approved_videos']}</div>
                </div>
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-4">
                    <div class="text-xs text-gray-400">Published to YouTube</div>
                    <div class="text-2xl font-black text-red-400 mt-1">{stats['published_videos']}</div>
                </div>
            </div>

            <!-- Ingestion Section -->
            <div class="bg-gray-800 border border-gray-700 rounded-xl p-6">
                <h2 class="text-lg font-bold text-white mb-4">🚀 Ingest Gameplay Footage & Run AI Pipeline</h2>
                <form action="/api/upload" method="post" enctype="multipart/form-data" class="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold text-gray-300 mb-1">Select Video File (.mp4, .mov, .mkv)</label>
                        <input type="file" name="file" required class="block w-full text-xs text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-pink-600 file:text-white hover:file:bg-pink-700 cursor-pointer bg-gray-900 rounded-lg border border-gray-700" />
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-gray-300 mb-1">Language</label>
                        <select name="language" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white">
                            <option value="hinglish" selected>Hinglish (Gaming Slang)</option>
                            <option value="hindi">Hindi (Devanagari)</option>
                            <option value="english">English (Global Gaming)</option>
                        </select>
                    </div>
                    <div>
                        <button type="submit" class="w-full bg-gradient-to-r from-pink-600 to-indigo-600 hover:from-pink-700 hover:to-indigo-700 text-white font-bold py-2 px-4 rounded-lg text-xs transition shadow-lg">
                            Analyze & Generate Shorts
                        </button>
                    </div>
                </form>
            </div>

            <!-- Clips Review List -->
            <div>
                <h2 class="text-xl font-bold text-white mb-4">🎬 Generated Shorts Review Queue</h2>
                <div class="space-y-4">
                    {clip_cards_html if clip_cards_html else '<div class="text-center py-12 text-gray-500 bg-gray-800 rounded-xl border border-gray-700">No clips generated yet. Upload video footage above to get started.</div>'}
                </div>
            </div>
        </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/api/upload")
async def upload_gameplay(
    file: UploadFile = File(...),
    language: str = Form("hinglish"),
    template_name: str = Form("cinematic_hype"),
):
    save_path = config.INPUT_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Trigger pipeline
    try:
        pipeline.process_video_pipeline(
            video_path=save_path,
            language=language,
            template_name=template_name,
            top_clips=3,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return HTMLResponse('<script>window.location.href = "/";</script>')


@app.post("/api/clips/{clip_id}/approve")
def approve_clip(clip_id: int):
    db.update_clip_status(clip_id, "approved")
    return HTMLResponse('<script>window.location.href = "/";</script>')


@app.post("/api/clips/{clip_id}/upload")
def upload_clip(clip_id: int):
    pipeline.approve_and_publish_clip(clip_id=clip_id, privacy_status="private")
    return HTMLResponse('<script>window.location.href = "/";</script>')


@app.get("/api/streams")
def list_discovered_streams(limit: int = 20):
    streams = db.list_discovered_streams(limit=limit)
    return JSONResponse(content={"streams": streams})


@app.get("/api/sessions")
def list_monitoring_sessions():
    sessions = db.get_active_monitoring_sessions()
    return JSONResponse(content={"active_sessions": sessions})


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: int):
    job = db.get_processing_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content=job)


@app.post("/api/jobs")
def create_job(payload: dict):
    job_type = payload.get("job_type", "highlight_render")
    job_payload = payload.get("payload", {})
    priority = payload.get("priority", 10)
    job_id = db.enqueue_processing_job(job_type, job_payload, priority=priority)
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued"})


if __name__ == "__main__":
    print(f"Starting GTA 6 AI Shorts Automation Web Dashboard on http://127.0.0.1:8501 ...")
    uvicorn.run(app, host="127.0.0.1", port=8501)
