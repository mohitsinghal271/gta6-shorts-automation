"""
Master Pipeline Orchestrator
Coordinates the full end-to-end processing lifecycle from raw video ingestion to final YouTube Short.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from config import config
from database.db import db
from modules.gameplay_ingestion import ingestion_service
from modules.scene_detector import scene_detector
from modules.video_analyzer import video_analyzer
from modules.semantic_analyzer import semantic_analyzer
from modules.highlight_ranker import highlight_ranker
from modules.clip_generator import clip_generator
from modules.voice_generator import voice_generator
from modules.video_editor import video_editor
from modules.metadata_generator import metadata_generator
from modules.youtube_uploader import youtube_uploader
from modules.publishing_policy import publishing_policy

logger = logging.getLogger("gta6_agent.pipeline")


class PipelineOrchestrator:
    def process_video_pipeline(
        self,
        video_path: Path,
        language: str = "hinglish",
        template_name: str = "cinematic_hype",
        include_voiceover: bool = True,
        top_clips: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes full end-to-end pipeline on a video file:
        1. Ingestion & probing
        2. Scene detection
        3. Multi-modal AI analysis (motion, audio, hook, unpredictability)
        4. Semantic AI gameplay analysis (Keyframes + VLM metrics)
        5. Highlight ranking & deduplication
        6. Sub-clip extraction
        7. Voiceover synthesis & timed word alignment
        8. ASS karaoke subtitle generation & vertical 9:16 rendering
        9. High-CTR metadata generation
        """
        video_path = Path(video_path).resolve()
        logger.info(f"--- Starting Full Pipeline for: {video_path.name} ---")

        # Step 1: Ingestion
        video_id, metadata = ingestion_service.ingest_video_file(video_path)

        # Step 2: Scene Detection
        scenes = scene_detector.process_and_save_scenes(
            video_id=video_id,
            video_path=video_path,
            duration=metadata.duration_seconds,
        )

        # Step 3: Video AI Analysis
        audio_profile = video_analyzer.extract_audio_rms_profile(video_path)
        segments = video_analyzer.analyze_sliding_windows(
            video_path=video_path,
            duration=metadata.duration_seconds,
            scenes=scenes,
            window_duration=config.video.target_duration_max,
            audio_profile=audio_profile,
        )

        # Step 4: Heuristic CV/Audio Pre-Ranking Shortlist
        # Do not run VLM frame extraction on all sliding-window candidates.
        # Shortlist the top promising candidates first (default 15).
        shortlist_size = getattr(getattr(config, "pipeline", None), "semantic_shortlist_size", 15)
        shortlisted_segments = highlight_ranker.rank_and_deduplicate(segments, top_n=shortlist_size)

        # Step 5: Semantic AI Gameplay Analysis ONLY on shortlisted candidates
        for seg in shortlisted_segments:
            try:
                sem_res = semantic_analyzer.analyze_clip_semantics(
                    video_path=video_path,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    scenes=scenes,
                    audio_profile=audio_profile,
                )
                seg.semantic_score = sem_res.composite_score
                seg.humor_score = sem_res.humor_score
                seg.stunt_score = sem_res.stunt_score
                seg.cinematic_score = sem_res.cinematic_score
                seg.event_summary = sem_res.event_summary
                seg.why_entertaining = sem_res.why_entertaining
                seg.suggested_hook = sem_res.suggested_hook
                seg.keyframe_timestamps = sem_res.keyframe_timestamps
                seg.is_fallback = sem_res.is_fallback
                seg.semantic_is_fallback = sem_res.is_fallback
                seg.semantic_status = "FALLBACK" if sem_res.is_fallback else "SUCCESS"
            except Exception as e:
                logger.warning(f"Semantic analysis failed for segment {seg.start_time}-{seg.end_time}: {e}")
                seg.is_fallback = True
                seg.semantic_is_fallback = True
                seg.semantic_status = "FAILED"
                seg.semantic_score = 0.0

        # Step 6: Highlight Ranking & Deduplication (re-ranking shortlist with semantic scores)
        ranked = highlight_ranker.rank_and_deduplicate(shortlisted_segments, top_n=top_clips)

        # Step 7: Candidate Clip Extraction
        candidates = clip_generator.generate_candidate_clips(
            video_id=video_id,
            input_path=video_path,
            ranked_segments=ranked,
            language=language,
            template_name=template_name,
        )

        final_clips = []
        for cand in candidates:
            clip_id = cand["clip_id"]
            cand_path = Path(cand["candidate_path"])
            duration = cand["duration"]
            tags = cand["tags"]
            semantic_info = cand.get("semantic_info")

            # Step 8: Voiceover Generation
            voice_res = voice_generator.generate_voiceover(
                clip_id=clip_id,
                language=language,
                tags=tags,
                include_voiceover=include_voiceover,
                semantic_info=semantic_info,
            )

            # Step 9: Subtitle Generation & Final 9:16 Rendering
            final_video_path = video_editor.render_final_short(
                clip_id=clip_id,
                candidate_clip_path=cand_path,
                duration=duration,
                voiceover_result=voice_res,
                template_name=template_name,
            )

            # Save initial path with pending_review status
            db.update_clip_status(clip_id, status="pending_review", final_path=str(final_video_path))

            # Step 10: Metadata Generation
            meta_res = metadata_generator.generate_metadata(
                clip_id=clip_id,
                language=language,
                tags=tags,
                semantic_info=semantic_info,
            )

            # Step 11: Publishing Policy & Authorization Gate Evaluation
            meta_dict = {
                "title_recommended": meta_res.title_recommended,
                "title": meta_res.title_recommended,
                "description": meta_res.description,
                "tags": meta_res.tags,
            }
            cand_clip_record = db.get_clip_by_id(clip_id)
            policy_res = publishing_policy.evaluate(
                clip_id=clip_id,
                clip=cand_clip_record,
                video_path=final_video_path,
                metadata=meta_dict,
            )

            auto_pub = (
                getattr(getattr(config, "publishing", None), "auto_publish", False)
                or getattr(getattr(config, "youtube", None), "auto_publish", False)
                or getattr(getattr(config, "pipeline", None), "auto_publish", False)
            )

            clip_status = "pending_review"
            if policy_res.can_publish and auto_pub:
                logger.info(f"Clip {clip_id} satisfies 8-point publishing policy; auto-publishing.")
                db.set_clip_approval(clip_id, approved=True)
                upload_res = youtube_uploader.upload_short(
                    clip_id=clip_id,
                    video_path=final_video_path,
                    title=meta_res.title_recommended,
                    description=meta_res.description,
                    tags=meta_res.tags,
                    privacy_status=policy_res.privacy_status,
                )
                if upload_res.success:
                    clip_status = "published"
                else:
                    clip_status = "pending_review"

            final_clips.append(
                {
                    "clip_id": clip_id,
                    "final_path": str(final_video_path),
                    "engagement_score": cand["engagement_score"],
                    "title": meta_res.title_recommended,
                    "status": clip_status,
                    "policy_can_publish": policy_res.can_publish,
                }
            )

        db.update_gameplay_status(video_id, "analyzed")
        logger.info(
            f"--- Pipeline Completed for {video_path.name}: {len(final_clips)} ready ---"
        )
        return {
            "video_id": video_id,
            "filename": metadata.filename,
            "clips_generated": len(final_clips),
            "clips": final_clips,
        }

    def approve_clip(self, clip_id: int) -> Dict[str, Any]:
        """Dedicated approval gate for a clip."""
        clip = db.get_clip_by_id(clip_id)
        if not clip:
            raise ValueError(f"Clip ID {clip_id} not found.")
        db.set_clip_approval(clip_id, approved=True)
        return {"clip_id": clip_id, "status": "approved", "approved_for_upload": 1}

    def approve_and_publish_clip(
        self,
        clip_id: int,
        privacy_status: str = "private",
        scheduled_time: Optional[str] = None,
        simulate: Optional[bool] = None,
        enforce_approval: bool = True,
    ) -> Dict[str, Any]:
        """
        Publishing workflow:
        1. Checks that clip is already approved OR meets all 8 publishing policy rules for auto-publishing
        2. Retrieves final video path & metadata
        3. Uploads to YouTube via youtube_uploader
        """
        clip = db.get_clip_by_id(clip_id)
        if not clip:
            raise ValueError(f"Clip ID {clip_id} not found.")

        meta = db.get_metadata(clip_id)
        if not meta:
            raise ValueError(f"Metadata for clip ID {clip_id} not found.")

        final_path = clip.get("final_path") or clip.get("candidate_path")
        if not final_path or not Path(final_path).exists():
            raise FileNotFoundError(f"Final video file not found for clip ID {clip_id}")

        # Note: Do NOT auto-approve here; upload must require an existing approval
        # or satisfy all 8 rules of PublishingPolicy.
        # Upload
        upload_result = youtube_uploader.upload_short(
            clip_id=clip_id,
            video_path=Path(final_path),
            title=meta["title_recommended"],
            description=meta["description"],
            tags=meta["tags"],
            privacy_status=privacy_status,
            scheduled_publish_time=scheduled_time,
            simulate=simulate,
            enforce_approval=enforce_approval,
        )

        return {
            "clip_id": clip_id,
            "success": upload_result.success,
            "youtube_video_id": upload_result.youtube_video_id,
            "youtube_url": upload_result.youtube_url,
            "is_simulation": upload_result.is_simulation,
            "error_message": upload_result.error_message,
        }



pipeline = PipelineOrchestrator()
