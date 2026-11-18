"""
Publishing Policy & Authorization Gate Module
Enforces strict 8-point automated publishing criteria before allowing upload to YouTube.
Zero tolerance for unverified rights, fallback hallucinations, or non-compliant media.
"""

import os
import re
import sys
import json
import shutil
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from config import config
from database.db import db
from modules.duplicate_detector import duplicate_detector

logger = logging.getLogger("gta6_agent.publishing_policy")


@dataclass
class PolicyEvaluationResult:
    can_publish: bool
    status: str  # 'approved' or 'pending_review'
    reasons_failed: List[str] = field(default_factory=list)
    rule_results: Dict[str, bool] = field(default_factory=dict)
    privacy_status: str = "private"


class PublishingPolicy:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH

    def check_video_spec(self, video_path: Path) -> tuple[bool, str]:
        """
        Validates video exists, duration in [15.0, 60.0], vertical 1080x1920, and contains audio stream.
        Returns (valid: bool, reason: str).
        """
        if not video_path.exists():
            return False, "Video file does not exist"
        spec = self._probe_media_spec(video_path)
        dur = spec["duration"]
        if not (15.0 <= dur <= 60.0):
            return False, f"Duration {dur:.1f}s not in [15.0, 60.0]s"
        if not (spec["width"] == 1080 and spec["height"] == 1920):
            return False, f"Resolution {spec['width']}x{spec['height']} is not 1080x1920"
        if not spec["has_audio"]:
            return False, "Video file lacks required audio stream"
        return True, "OK"

    def evaluate(
        self,
        clip_id: Optional[int] = None,
        clip: Optional[Dict[str, Any]] = None,
        video_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_verified: Optional[bool] = None,
        semantic_is_fallback: Optional[bool] = None,
    ) -> PolicyEvaluationResult:
        """
        Evaluate candidate clip against 8 mandatory rules:
        1. Engagement score >= min_engagement_score (85.0)
        2. Source permission verified evidence == True
        3. Semantic analysis valid, not fallback (semantic_is_fallback == False)
        4. Video file exists, valid 1080x1920, duration in [15.0, 60.0]s
        5. Duplicate check passed (clip not already uploaded)
        6. Complete metadata present (recommended title, description, tags)
        7. If all pass and auto_publish is True -> auto-upload with configured privacy
        8. Otherwise -> place in review queue (status: pending_review)
        """
        reasons_failed: List[str] = []
        rule_results: Dict[str, bool] = {}

        # Load clip if needed
        if clip is None and clip_id is not None:
            clip = db.get_clip_by_id(clip_id)

        # 1. Rule: Engagement score >= threshold
        min_score = getattr(getattr(config, "publishing", None), "min_engagement_score", 85.0)
        engagement_score = 0.0
        if clip:
            engagement_score = float(clip.get("engagement_score") or 0.0)

        r1 = engagement_score >= min_score
        rule_results["engagement_score"] = r1
        if not r1:
            reasons_failed.append(
                f"Engagement score {engagement_score:.1f} below threshold {min_score:.1f}"
            )

        # 2. Rule: Source permission verified (evidence-backed)
        r2 = False
        if source_verified is not None:
            r2 = bool(source_verified)
        elif clip:
            video_id = clip.get("video_id")
            if video_id:
                gp = db.get_gameplay_by_id(video_id)
                if gp:
                    source_id = gp.get("source_id")
                    if source_id:
                        src = db.get_source_by_id(source_id)
                        if src and src.get("permission_verified") == 1:
                            # Verify evidence attributes
                            ev_type = src.get("evidence_type")
                            comm = src.get("commercial_reuse_allowed")
                            if ev_type and comm:
                                r2 = True
        else:
            r2 = False

        rule_results["source_permission_verified"] = r2
        if not r2:
            reasons_failed.append("Source copyright/reuse permission is not verified with evidence")

        # 3. Rule: Semantic analysis valid (not fallback, and must exist)
        r3 = False
        if semantic_is_fallback is not None:
            r3 = not bool(semantic_is_fallback)
        elif clip:
            status = clip.get("semantic_status")
            has_fb = clip.get("is_fallback")
            if has_fb is None:
                has_fb = clip.get("semantic_is_fallback")

            if status in ("FAILED", "FALLBACK"):
                r3 = False
            elif has_fb in (True, 1, "1"):
                r3 = False
            else:
                ev_summary = clip.get("event_summary") or ""
                if "GTA 6 gameplay sequence" in ev_summary and clip.get("semantic_score", 0.0) == 54.25:
                    r3 = False
                elif status == "SUCCESS":
                    r3 = True
                elif has_fb in (False, 0, "0") and (clip.get("semantic_score", 0.0) > 0.0 or clip.get("event_summary")):
                    r3 = True
                else:
                    # Missing semantic analysis -> fail closed!
                    r3 = False
        else:
            r3 = False

        rule_results["semantic_valid_not_fallback"] = r3
        if not r3:
            reasons_failed.append("Semantic analysis is missing, failed, or fallback; real VLM analysis required")

        # 4. Rule: Physical media inspection (duration, 1080x1920, audio stream)
        v_path = video_path
        if not v_path and clip:
            candidate = clip.get("final_path") or clip.get("candidate_path")
            if candidate:
                v_path = Path(candidate)

        r4 = False
        if v_path and Path(v_path).exists():
            spec = self._probe_media_spec(Path(v_path))
            dur = spec["duration"]
            is_dur_ok = 15.0 <= dur <= 60.0
            is_dim_ok = (spec["width"] == 1080 and spec["height"] == 1920)
            is_audio_ok = spec["has_audio"]

            if is_dur_ok and is_dim_ok and is_audio_ok:
                r4 = True
            else:
                if not is_dur_ok:
                    reasons_failed.append(f"Probed video duration {dur:.1f}s not in required [15.0, 60.0]s")
                if not is_dim_ok:
                    reasons_failed.append(f"Video resolution {spec['width']}x{spec['height']} is not vertical 1080x1920")
                if not is_audio_ok:
                    reasons_failed.append("Video file lacks required audio stream")
        else:
            reasons_failed.append(f"Video file does not exist at {v_path}")

        rule_results["video_spec_valid"] = r4

        # 5. Rule: Duplicate check passed
        r5 = True
        if clip_id is not None:
            r5 = not duplicate_detector.is_already_uploaded(clip_id)
        rule_results["duplicate_check_passed"] = r5
        if not r5:
            reasons_failed.append(f"Clip ID {clip_id} was already uploaded to YouTube")

        # 6. Rule: Metadata present
        meta_dict = metadata
        if not meta_dict and clip_id is not None:
            meta_dict = db.get_metadata(clip_id)

        r6 = False
        if meta_dict:
            title = meta_dict.get("title_recommended") or meta_dict.get("title")
            desc = meta_dict.get("description")
            tags = meta_dict.get("tags")
            if title and desc and tags and len(tags) > 0:
                r6 = True
        rule_results["metadata_present"] = r6
        if not r6:
            reasons_failed.append("Metadata missing: title, description, and tags are required")

        # Final verdict
        can_publish = all([r1, r2, r3, r4, r5, r6])
        status = "approved" if can_publish else "pending_review"

        default_priv = getattr(
            getattr(config, "publishing", None),
            "default_privacy",
            getattr(getattr(config, "youtube", None), "default_privacy", "private"),
        )

        return PolicyEvaluationResult(
            can_publish=can_publish,
            status=status,
            reasons_failed=reasons_failed,
            rule_results=rule_results,
            privacy_status=default_priv,
        )

    def _probe_media_spec(self, video_path: Path) -> Dict[str, Any]:
        """
        Uses ffprobe / ffmpeg to inspect the physical video container on disk.
        Extracts real container duration, width, height, and audio streams.
        """
        spec = {"duration": 0.0, "width": 0, "height": 0, "has_audio": False}
        if not video_path.exists():
            return spec

        # 1. Try ffprobe JSON output
        ffprobe_bin = os.environ.get("FFPROBE_PATH") or shutil.which("ffprobe")
        if not ffprobe_bin and self.ffmpeg_path:
            cand = Path(self.ffmpeg_path).parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if cand.is_file():
                ffprobe_bin = str(cand)

        if ffprobe_bin:
            try:
                cmd = [
                    ffprobe_bin,
                    "-v", "error",
                    "-show_entries", "stream=codec_type,width,height,duration",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(video_path),
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0)
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout)
                    fmt = data.get("format", {})
                    if fmt.get("duration"):
                        try:
                            spec["duration"] = float(fmt["duration"])
                        except ValueError:
                            pass
                    streams = data.get("streams", [])
                    for s in streams:
                        ctype = s.get("codec_type")
                        if ctype == "video" and s.get("width") and s.get("height"):
                            spec["width"] = int(s["width"])
                            spec["height"] = int(s["height"])
                            if spec["duration"] == 0.0 and s.get("duration"):
                                try:
                                    spec["duration"] = float(s["duration"])
                                except ValueError:
                                    pass
                        elif ctype == "audio":
                            spec["has_audio"] = True
                    if spec["duration"] > 0.0:
                        return spec
            except Exception:
                pass

        # 2. Fallback to ffmpeg -hide_banner -i
        try:
            cmd = [self.ffmpeg_path, "-hide_banner", "-i", str(video_path)]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0)
            out = res.stderr
            match_d = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
            if match_d:
                h, m, s = match_d.groups()
                spec["duration"] = int(h) * 3600 + int(m) * 60 + float(s)

            match_r = re.search(r"Stream #.*?Video:.*?,.*?(\d{3,4})x(\d{3,4})", out)
            if match_r:
                spec["width"] = int(match_r.group(1))
                spec["height"] = int(match_r.group(2))
            elif "1080x1920" in out:
                spec["width"] = 1080
                spec["height"] = 1920

            if re.search(r"Stream #.*?Audio:", out):
                spec["has_audio"] = True
        except Exception:
            pass

        return spec

    def _probe_duration(self, video_path: Path) -> float:
        return self._probe_media_spec(video_path)["duration"]

    def _probe_resolution(self, video_path: Path) -> bool:
        spec = self._probe_media_spec(video_path)
        return spec["width"] == 1080 and spec["height"] == 1920


publishing_policy = PublishingPolicy()
