"""
Semantic AI Gameplay Analysis Module
Extracts intelligent keyframes (Hook, Actual Motion/Audio Peak, Climax), analyzes them
with Vision Language Models (Moondream / Qwen Vision / Ollama), evaluates entertainment metrics
(humor, stunt, cinematic scores), and generates contextual event summaries and hooks.
"""

import os
import json
import base64
import logging
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# Fix 1: Explicit NumPy import
import numpy as np

from config import config

logger = logging.getLogger("gta6_agent.semantic_analyzer")


@dataclass
class KeyframeRef:
    timestamp: float
    role: str

    def __float__(self):
        return self.timestamp


@dataclass
class SemanticAnalysisResult:
    humor_score: float
    stunt_score: float
    cinematic_score: float
    composite_score: float
    event_summary: str
    why_entertaining: str
    suggested_hook: str
    keyframe_timestamps: List[float] = field(default_factory=list)
    raw_response: Optional[str] = None
    is_fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "humor_score": self.humor_score,
            "stunt_score": self.stunt_score,
            "cinematic_score": self.cinematic_score,
            "composite_score": self.composite_score,
            "event_summary": self.event_summary,
            "why_entertaining": self.why_entertaining,
            "suggested_hook": self.suggested_hook,
            "keyframe_timestamps": self.keyframe_timestamps,
            "is_fallback": self.is_fallback,
        }


def calculate_semantic_composite(
    stunt_score: float, humor_score: float, cinematic_score: float
) -> float:
    """
    Fix 3: Calculate composite semantic score with weights:
    40% Stunt + 35% Humor + 25% Cinematic
    Fallback verification: 0.40 * 50.0 + 0.35 * 55.0 + 0.25 * 60.0 = 54.25
    """
    w_stunt = getattr(getattr(config, "semantic", None), "weight_stunt", 0.40)
    w_humor = getattr(getattr(config, "semantic", None), "weight_humor", 0.35)
    w_cinematic = getattr(getattr(config, "semantic", None), "weight_cinematic", 0.25)
    score = (w_stunt * float(stunt_score)) + (w_humor * float(humor_score)) + (w_cinematic * float(cinematic_score))
    return round(score, 2)


class SemanticAnalyzer:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or config.FFMPEG_PATH
        # Default fallback values
        self.fallback_stunt = 50.0
        self.fallback_humor = 55.0
        self.fallback_cinematic = 60.0
        self.connect_timeout = getattr(getattr(config, "semantic", None), "connect_timeout_seconds", 5.0)
        self.inference_timeout = getattr(getattr(config, "semantic", None), "inference_timeout_seconds", 60.0)

    def find_action_peak_timestamp(
        self,
        start_time: float,
        end_time: float,
        scenes: Optional[List[Any]] = None,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
    ) -> float:
        """
        Fix 2: Find the actual motion/audio peak rather than a fixed (duration * 0.5) timestamp.
        Uses motion score profile from scene detector and audio RMS energy profile.
        Safely supports both dicts and SceneBoundary objects.
        Cleanly falls back to midpoint if video is silent or has zero motion.
        """
        duration = max(0.1, end_time - start_time)
        fallback_mid = start_time + (duration * 0.5)

        def _get_val(obj: Any, key: str, default: float = 0.0) -> float:
            if isinstance(obj, dict):
                return float(obj.get(key, default))
            return float(getattr(obj, key, default))

        # 1. Evaluate audio energy peaks in [start_time, end_time]
        peak_audio_time = None
        max_audio_energy = 0.0
        if audio_profile:
            window_audio = [(t, e) for t, e in audio_profile if start_time <= t <= end_time]
            if window_audio:
                best_t, best_e = max(window_audio, key=lambda item: item[1])
                if best_e > 0.0:  # Only count real audio energy above silence
                    peak_audio_time = best_t
                    max_audio_energy = best_e

        # 2. Evaluate motion score peaks in [start_time, end_time]
        peak_motion_time = None
        max_motion_score = 0.0
        if scenes:
            sub_scenes = [
                s for s in scenes
                if not (_get_val(s, "end_time") <= start_time or _get_val(s, "start_time") >= end_time)
            ]
            if sub_scenes:
                best_scene = max(sub_scenes, key=lambda s: _get_val(s, "motion_score"))
                s_m = _get_val(best_scene, "motion_score")
                if s_m > 0.0:  # Only count real motion
                    s_start = max(start_time, _get_val(best_scene, "start_time", start_time))
                    s_end = min(end_time, _get_val(best_scene, "end_time", end_time))
                    peak_motion_time = (s_start + s_end) / 2.0
                    max_motion_score = s_m

        # 3. Combine motion and audio signals
        if peak_motion_time is not None and peak_audio_time is not None:
            norm_motion = min(1.0, max_motion_score / 40.0)
            norm_audio = min(1.0, max_audio_energy / 80.0)
            if norm_motion + norm_audio > 0:
                w_motion = norm_motion / (norm_motion + norm_audio)
                w_audio = norm_audio / (norm_motion + norm_audio)
                peak_time = (w_motion * peak_motion_time) + (w_audio * peak_audio_time)
            else:
                peak_time = fallback_mid
        elif peak_motion_time is not None:
            peak_time = peak_motion_time
        elif peak_audio_time is not None:
            peak_time = peak_audio_time
        else:
            peak_time = fallback_mid

        # Ensure peak action frame is safely padded inside the window
        pad = min(1.0, max(0.05, duration * 0.15))
        clamped_peak = max(start_time + pad, min(end_time - pad, peak_time))
        return round(float(clamped_peak), 2)

    def extract_intelligent_keyframes(
        self,
        start_time: float,
        end_time: float,
        scenes: Optional[List[Any]] = None,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
    ) -> List[float]:
        """
        Extract 3 keyframe timestamps:
        1. Hook frame (near start, within first 0.5-1.5s)
        2. Peak action frame (actual motion/audio peak)
        3. Climax / Resolution frame (near end, within final 1.0-2.0s)
        Guarantees strictly ascending order: start <= hook < peak < climax <= end.
        """
        duration = max(0.1, end_time - start_time)
        eps = min(0.1, duration / 4.0)

        # Hook: at start + min(1.0, duration * 0.08)
        hook_t = round(start_time + max(eps, min(1.0, duration * 0.08)), 2)

        # Peak: actual motion/audio peak
        peak_t = self.find_action_peak_timestamp(start_time, end_time, scenes, audio_profile)

        # Climax: near end
        climax_t = round(end_time - max(eps, min(1.5, duration * 0.10)), 2)

        # Ensure strictly ascending order: start <= hook < peak < climax <= end
        if hook_t >= climax_t:
            hook_t = round(start_time + eps, 2)
            climax_t = round(end_time - eps, 2)

        if peak_t <= hook_t:
            peak_t = round(hook_t + max(eps, (climax_t - hook_t) * 0.5), 2)
        elif peak_t >= climax_t:
            peak_t = round(hook_t + max(eps, (climax_t - hook_t) * 0.5), 2)

        if climax_t <= peak_t:
            climax_t = round(min(end_time, peak_t + eps), 2)
        if peak_t <= hook_t:
            hook_t = round(max(start_time, peak_t - eps), 2)

        return [hook_t, peak_t, climax_t]

    def select_keyframes(
        self,
        start_time: float,
        end_time: float,
        video_path: Optional[Path] = None,
        scenes: Optional[List[Any]] = None,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
        motion_scores: Optional[List[float]] = None,
        audio_energies: Optional[List[float]] = None,
    ) -> List[KeyframeRef]:
        """Convenience method returning keyframe objects with timestamps and roles."""
        if motion_scores and not scenes:
            duration = max(0.1, end_time - start_time)
            dt = duration / max(1, len(motion_scores))
            scenes = [
                {"start_time": start_time + i * dt, "end_time": start_time + (i + 1) * dt, "motion_score": m}
                for i, m in enumerate(motion_scores)
            ]
        if audio_energies and not audio_profile:
            duration = max(0.1, end_time - start_time)
            dt = duration / max(1, len(audio_energies))
            audio_profile = [
                (start_time + i * dt, e)
                for i, e in enumerate(audio_energies)
            ]
        ts_list = self.extract_intelligent_keyframes(start_time, end_time, scenes, audio_profile)
        roles = ["hook", "peak", "climax"]
        return [KeyframeRef(timestamp=t, role=r) for t, r in zip(ts_list, roles)]

    def extract_frame_bytes(self, video_path: Path, timestamp: float) -> Optional[bytes]:
        """Extract a single JPEG frame at timestamp using FFmpeg."""
        try:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-vframes",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "-",
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
            if proc.returncode == 0 and len(proc.stdout) > 100:
                return proc.stdout
        except Exception as e:
            logger.debug(f"Frame extraction at {timestamp}s failed: {e}")
        return None

    def get_factual_fallback_result(
        self, keyframe_timestamps: Optional[List[float]] = None
    ) -> SemanticAnalysisResult:
        """
        Fix 5: Generic fallback commentary: Never invent events when VLM is unavailable.
        Uses factual, neutral descriptions instead of hallucinating fake occurrences.
        Fix 3: Fallback composite score: 0.40 * 50 + 0.35 * 55 + 0.25 * 60 = 54.25
        """
        composite = calculate_semantic_composite(
            stunt_score=self.fallback_stunt,
            humor_score=self.fallback_humor,
            cinematic_score=self.fallback_cinematic,
        )
        return SemanticAnalysisResult(
            humor_score=self.fallback_humor,
            stunt_score=self.fallback_stunt,
            cinematic_score=self.fallback_cinematic,
            composite_score=composite,
            event_summary="GTA 6 gameplay sequence",
            why_entertaining="High visual action and dynamic gameplay pacing.",
            suggested_hook="Check out this GTA 6 gameplay sequence!",
            keyframe_timestamps=keyframe_timestamps or [],
            is_fallback=True,
        )

    def validate_and_parse_response(
        self,
        raw_text: str,
        keyframe_timestamps: Optional[List[float]] = None,
    ) -> SemanticAnalysisResult:
        """
        Fix 4: Robust response validation:
        - Parse JSON safely (handling markdown fences, extra text, etc.)
        - Support percentage and ratio string formats ("85%", "90/100")
        - Support common VLM field aliases (summary, hook, stunt, humor, cinematic)
        - Ensure scores are clamped to [0.0, 100.0]
        - Handle malformed/partial VLM outputs gracefully with safe defaults
        """
        if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
            return self.get_factual_fallback_result(keyframe_timestamps)

        cleaned = raw_text.strip()

        # Handle markdown fences robustly (including single-line and multiline blocks)
        import re
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fence_match:
            candidate_inside = fence_match.group(1).strip()
            if candidate_inside:
                cleaned = candidate_inside

        # Try parsing JSON candidates: first try largest {...}, then find any valid JSON object
        data = None
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                parsed = json.loads(cleaned[start_idx : end_idx + 1])
                if isinstance(parsed, dict):
                    data = parsed
            except Exception:
                pass

        # If outermost failed, scan for all JSON substrings
        if data is None:
            matches = re.findall(r"\{[^{}]*\}", cleaned)
            for m in reversed(matches):
                try:
                    parsed = json.loads(m)
                    if isinstance(parsed, dict):
                        data = parsed
                        break
                except Exception:
                    continue

        if not data or not isinstance(data, dict):
            logger.warning("No valid JSON found in VLM response; defaulting to factual fallback.")
            return self.get_factual_fallback_result(keyframe_timestamps)

        # Validate and clamp score fields (supports numeric, percentages, string formats)
        def parse_score(val: Any, default_val: float) -> float:
            if val is None:
                return default_val
            try:
                if isinstance(val, str):
                    val = val.strip().rstrip("%")
                    if "/" in val:
                        parts = val.split("/")
                        val = float(parts[0]) / float(parts[1]) * 100.0
                num = float(val)
                if np.isnan(num) or np.isinf(num):
                    return default_val
                return max(0.0, min(100.0, round(num, 1)))
            except (ValueError, TypeError, ZeroDivisionError):
                return default_val

        # Support aliases for score keys
        humor_val = data.get("humor_score") if data.get("humor_score") is not None else (data.get("humor") or data.get("humour_score"))
        stunt_val = data.get("stunt_score") if data.get("stunt_score") is not None else (data.get("stunt") or data.get("action_score"))
        cinematic_val = data.get("cinematic_score") if data.get("cinematic_score") is not None else (data.get("cinematic") or data.get("visual_score"))

        humor = parse_score(humor_val, self.fallback_humor)
        stunt = parse_score(stunt_val, self.fallback_stunt)
        cinematic = parse_score(cinematic_val, self.fallback_cinematic)

        # Validate string fields with aliases
        event_summary = str(
            data.get("event_summary")
            or data.get("summary")
            or data.get("description")
            or data.get("event")
            or ""
        ).strip()
        if not event_summary:
            event_summary = "GTA 6 gameplay sequence"

        why_entertaining = str(
            data.get("why_entertaining")
            or data.get("entertainment_value")
            or data.get("why")
            or ""
        ).strip()
        if not why_entertaining:
            why_entertaining = "High visual action and dynamic gameplay pacing."

        suggested_hook = str(
            data.get("suggested_hook")
            or data.get("hook")
            or data.get("short_hook")
            or ""
        ).strip()
        if not suggested_hook:
            suggested_hook = "Check out this GTA 6 gameplay sequence!"

        composite = calculate_semantic_composite(
            stunt_score=stunt,
            humor_score=humor,
            cinematic_score=cinematic,
        )

        return SemanticAnalysisResult(
            humor_score=humor,
            stunt_score=stunt,
            cinematic_score=cinematic,
            composite_score=composite,
            event_summary=event_summary,
            why_entertaining=why_entertaining,
            suggested_hook=suggested_hook,
            keyframe_timestamps=keyframe_timestamps or [],
            raw_response=raw_text,
            is_fallback=False,
        )

    def analyze_segment(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        scenes: Optional[List[Dict[str, Any]]] = None,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
        mock_response: Optional[str] = None,
    ) -> SemanticAnalysisResult:
        """
        Analyze a candidate segment by extracting keyframes and querying the Vision Language Model.
        Supports Moondream / Qwen Vision via local Ollama / REST endpoints with graceful offline fallback.
        """
        keyframes = self.extract_intelligent_keyframes(start_time, end_time, scenes, audio_profile)

        # If a mock response is provided (e.g. for testing)
        if mock_response is not None:
            return self.validate_and_parse_response(mock_response, keyframe_timestamps=keyframes)

        # Check if VLM is enabled in configuration
        vlm_enabled = getattr(getattr(config, "semantic", None), "enabled", True)
        if not vlm_enabled:
            return self.get_factual_fallback_result(keyframes)

        vlm_endpoint = getattr(
            getattr(config, "semantic", None),
            "vlm_endpoint",
            os.environ.get("VLM_ENDPOINT", "http://localhost:11434/api/generate"),
        )
        model_name = getattr(
            getattr(config, "semantic", None),
            "model_name",
            os.environ.get("VLM_MODEL", "moondream"),
        )

        # Attempt to extract frames for VLM request
        frame_bytes_list = []
        for kt in keyframes:
            fb = self.extract_frame_bytes(video_path, kt)
            if fb:
                frame_bytes_list.append(base64.b64encode(fb).decode("utf-8"))

        if not frame_bytes_list:
            # Cannot extract frames or video unreachable
            return self.get_factual_fallback_result(keyframes)

        prompt = (
            "You are an expert gaming video analyst. Analyze these 3 keyframes (Hook, Peak Action Moment, Climax/Resolution) from a GTA 6 gameplay clip.\n"
            "Evaluate the gameplay on:\n"
            "1. humor_score: (0 to 100) How funny, unexpected, glitchy, or humorous the moment is.\n"
            "2. stunt_score: (0 to 100) How impressive, high-speed, acrobatic, or skilled the driving/action stunt is.\n"
            "3. cinematic_score: (0 to 100) Visual aesthetics, camera framing, lighting, and neon Vice City atmosphere.\n"
            "4. event_summary: A concise, factual summary (1-2 sentences) of the gameplay action shown.\n"
            "5. why_entertaining: A short explanation of what makes this clip entertaining or viral.\n"
            "6. suggested_hook: A catchy, high-CTR hook sentence for YouTube Shorts (under 10 words).\n\n"
            "Respond ONLY with valid JSON in this exact structure:\n"
            "{\n"
            '  "humor_score": 65.0,\n'
            '  "stunt_score": 85.0,\n'
            '  "cinematic_score": 75.0,\n'
            '  "event_summary": "...",\n'
            '  "why_entertaining": "...",\n'
            '  "suggested_hook": "..."\n'
            "}"
        )

        try:
            import requests

            timeout = (self.connect_timeout, self.inference_timeout)
            payload = {
                "model": model_name,
                "prompt": prompt,
                "images": frame_bytes_list,
                "stream": False,
                "format": "json",
            }
            resp = requests.post(vlm_endpoint, json=payload, timeout=timeout)
            if resp.status_code == 200:
                res_json = resp.json()
                raw_text = res_json.get("response") or res_json.get("content") or ""
                return self.validate_and_parse_response(raw_text, keyframe_timestamps=keyframes)
        except Exception as e:
            logger.debug(f"VLM endpoint unreachable ({e}). Using factual fallback.")

        return self.get_factual_fallback_result(keyframes)

    def analyze_clip_semantics(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        scenes: Optional[List[Dict[str, Any]]] = None,
        audio_profile: Optional[List[Tuple[float, float]]] = None,
        mock_response: Optional[str] = None,
    ) -> SemanticAnalysisResult:
        """Alias for analyze_segment for seamless API compatibility."""
        return self.analyze_segment(
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            scenes=scenes,
            audio_profile=audio_profile,
            mock_response=mock_response,
        )


semantic_analyzer = SemanticAnalyzer()

