"""
Streamlit Web Dashboard for GTA 6 AI YouTube Shorts Automation Agent
Run with: streamlit run app.py
"""

import os
import json
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    print("Streamlit is not installed in current environment.")
    print("To run the Streamlit dashboard: pip install streamlit && streamlit run app.py")
    print("Alternatively, run the built-in standalone web dashboard: python web_app.py")
    exit(0)

from config import config
from database.db import db
from modules.gameplay_ingestion import ingestion_service
from modules.pipeline import pipeline

st.set_page_config(
    page_title="GTA 6 AI Shorts Automation",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌴 GTA 6 AI YouTube Shorts Automation Agent")
st.caption("Automated highlight extraction, vertical 9:16 editing, multilingual commentary & YouTube publishing")

# Sidebar Controls
st.sidebar.header("⚙️ Agent Settings")
selected_lang = st.sidebar.selectbox("Language Mode", ["hinglish", "hindi", "english"], index=0)
selected_template = st.sidebar.selectbox(
    "Editing Template",
    ["cinematic_hype", "action_fast", "story_npc", "funny_moments"],
    index=0,
)
include_voice = st.sidebar.checkbox("Include AI Voiceover & Subtitles", value=True)
simulate_upload = st.sidebar.checkbox("Simulation Mode (Dry Run)", value=True)

# Overview KPIs
stats = db.get_dashboard_stats()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Videos Ingested", stats["total_videos_processed"])
col2.metric("Clips Generated", stats["total_clips_generated"])
col3.metric("Pending Review", stats["pending_review"])
col4.metric("Approved Clips", stats["approved_videos"])
col5.metric("Published Shorts", stats["published_videos"])

st.divider()

# Tab layout
tab_review, tab_upload, tab_history = st.tabs(
    ["🎬 Clip Review & Approval", "📤 Ingest & Process Footage", "📊 Publishing History"]
)

with tab_upload:
    st.subheader("Mode A: Upload Gameplay Footage")
    uploaded_file = st.file_uploader(
        "Upload GTA 6 MP4/MOV/MKV video", type=["mp4", "mov", "mkv", "avi", "webm"]
    )

    if uploaded_file is not None:
        save_path = config.INPUT_DIR / uploaded_file.name
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Uploaded {uploaded_file.name} to {save_path}")

        if st.button("🚀 Run Full AI Shorts Pipeline"):
            with st.spinner("Analyzing gameplay, extracting highlights, rendering 9:16 Shorts..."):
                try:
                    result = pipeline.process_video_pipeline(
                        video_path=save_path,
                        language=selected_lang,
                        template_name=selected_template,
                        include_voiceover=include_voice,
                        top_clips=3,
                    )
                    st.success(f"Generated {result['clips_generated']} viral candidate Shorts!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing video: {e}")

    st.subheader("Watched Folder Monitor")
    st.write(f"Folder: `{config.INPUT_DIR}`")
    if st.button("🔄 Scan Input Folder Now"):
        ingested = ingestion_service.scan_and_ingest_input_folder()
        st.info(f"Ingested {len(ingested)} new files.")
        st.rerun()

with tab_review:
    st.subheader("Clips Pending Review & Approval")
    clips = db.list_clips(limit=50)

    if not clips:
        st.info("No clips generated yet. Upload or scan footage in the 'Ingest & Process' tab.")
    else:
        for clip in clips:
            meta = db.get_metadata(clip["id"])
            title = meta["title_recommended"] if meta else f"Clip #{clip['id']}"

            with st.expander(
                f"[{clip['status'].upper()}] {title} (Engagement Score: {clip['engagement_score']} / 100)",
                expanded=(clip["status"] == "pending_review"),
            ):
                c_col1, c_col2 = st.columns([1, 1])

                with c_col1:
                    video_file = clip["final_path"] or clip["candidate_path"]
                    if video_file and os.path.exists(video_file):
                        st.video(video_file)
                    else:
                        st.warning("Video file not found.")

                with c_col2:
                    st.markdown(f"**Duration:** {clip['duration']}s | **Language:** {clip['language']}")
                    st.markdown(f"**Tags:** {', '.join(clip['scene_tags'])}")

                    # Metrics breakdown
                    st.progress(clip["visual_score"] / 100.0, text=f"Visual Excitement: {clip['visual_score']}%")
                    st.progress(clip["action_score"] / 100.0, text=f"Action Intensity: {clip['action_score']}%")
                    st.progress(clip["hook_score"] / 100.0, text=f"Hook Potential: {clip['hook_score']}%")

                    if meta:
                        st.markdown("**YouTube Titles:**")
                        for t in meta["titles"]:
                            st.write(f"- {t}")
                        st.text_area("Description Preview", meta["description"][:300] + "...", height=100)

                    # Controls
                    btn_col1, btn_col2 = st.columns(2)
                    if clip["status"] == "pending_review":
                        if btn_col1.button("✅ Approve Clip", key=f"appr_{clip['id']}"):
                            db.update_clip_status(clip["id"], "approved")
                            st.success("Approved!")
                            st.rerun()

                    if clip["status"] in ["approved", "pending_review"]:
                        if btn_col2.button("📤 Upload to YouTube", key=f"up_{clip['id']}"):
                            with st.spinner("Uploading to YouTube..."):
                                res = pipeline.approve_and_publish_clip(
                                    clip_id=clip["id"],
                                    privacy_status="private",
                                    simulate=simulate_upload,
                                )
                                if res["success"]:
                                    st.success(f"Uploaded! URL: {res['youtube_url']}")
                                    st.rerun()
                                else:
                                    st.error(f"Upload failed: {res['error_message']}")

with tab_history:
    st.subheader("YouTube Publishing History")
    history = db.get_publishing_history()
    if not history:
        st.write("No videos published yet.")
    else:
        for h in history:
            st.write(
                f"**Clip #{h['clip_id']}** | Status: `{h['upload_status']}` | Privacy: `{h['privacy_status']}` | Time: {h['published_at']}"
            )
            if h["youtube_url"]:
                st.markdown(f"🔗 [Watch on YouTube]({h['youtube_url']})")
            if h["error_log"]:
                st.error(h["error_log"])
            st.divider()
