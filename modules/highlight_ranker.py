"""
Highlight Ranker Module
Ranks candidate segments by composite engagement score, eliminates repetitive/duplicate scenes
via temporal Intersection over Union (IoU) non-maximum suppression, and selects the best candidate clips.
"""

import logging
from typing import List, Dict, Any, Optional
from modules.video_analyzer import SegmentAnalysis
from config import config

logger = logging.getLogger("gta6_agent.highlight_ranker")


class HighlightRanker:
    def __init__(self, max_overlap_iou: float = 0.30):
        """
        :param max_overlap_iou: Maximum allowed temporal overlap ratio between any two selected clips.
                                Suppresses duplicate / repetitive scenes.
        """
        self.max_overlap_iou = max_overlap_iou
        self.min_duration = config.video.min_clip_duration
        self.max_duration = config.video.max_clip_duration

    def calculate_temporal_iou(
        self, start1: float, end1: float, start2: float, end2: float
    ) -> float:
        """Compute 1D temporal Intersection over Union between two time windows."""
        intersection_start = max(start1, start2)
        intersection_end = min(end1, end2)
        intersection = max(0.0, intersection_end - intersection_start)

        union = (end1 - start1) + (end2 - start2) - intersection
        if union <= 0.0:
            return 0.0
        return intersection / union

    def calculate_semantic_ranking_score(
        self,
        segment: SegmentAnalysis,
        semantic_score: Optional[float] = None,
        is_fallback: Optional[bool] = None,
    ) -> float:
        """
        Combine motion dynamics, audio energy, and semantic AI score (humor, stunt, cinematic).
        If is_fallback is True, ignore the semantic score in ranking calculation
        (use purely the CV/audio composite score).
        Configurable weights default to:
        35% Motion dynamics (visual excitement + action intensity)
        15% Audio energy
        25% Semantic AI score (humor, stunt, cinematic)
        15% Hook potential
        10% Ending resolution quality
        """
        fallback = is_fallback
        if fallback is None:
            fallback = getattr(segment, "is_fallback", False) or getattr(segment, "semantic_is_fallback", False)

        if fallback:
            # Exclude fallback semantic scores from ranking; rely purely on CV/audio composite
            return segment.composite_score

        sem_score = semantic_score if semantic_score is not None else segment.semantic_score
        if sem_score is None:
            return segment.composite_score

        w_motion = getattr(getattr(config, "ranking", None), "weight_motion", 0.35)
        w_audio = getattr(getattr(config, "ranking", None), "weight_audio", 0.15)
        w_sem = getattr(getattr(config, "ranking", None), "weight_semantic", 0.25)
        w_hook = getattr(getattr(config, "ranking", None), "weight_hook", 0.15)
        w_ending = getattr(getattr(config, "ranking", None), "weight_ending", 0.10)

        motion_score = (segment.visual_excitement * 0.45) + (segment.action_intensity * 0.55)
        audio_score = segment.audio_intensity

        combined = (
            (motion_score * w_motion)
            + (audio_score * w_audio)
            + (float(sem_score) * w_sem)
            + (segment.hook_potential * w_hook)
            + (segment.ending_quality * w_ending)
        )
        return round(float(combined), 1)

    def rank_and_deduplicate(
        self,
        segments: List[SegmentAnalysis],
        top_n: int = 5,
        semantic_scores: Optional[Dict[int, float]] = None,
    ) -> List[SegmentAnalysis]:
        """
        Apply Non-Maximum Suppression (NMS) over candidate segments based on their engagement score.
        Incorporates semantic AI scores if present on the segment or provided in semantic_scores dict.
        Ensures diverse, non-overlapping, high-intensity clips are selected.
        """
        # Re-compute composite scores if semantic scores are provided
        if semantic_scores or any(s.semantic_score is not None for s in segments):
            for idx, s in enumerate(segments):
                sem = None
                if semantic_scores:
                    sem = semantic_scores.get(idx)
                    if sem is None:
                        sem = semantic_scores.get((s.start_time, s.end_time))
                if sem is None:
                    sem = s.semantic_score
                s.composite_score = self.calculate_semantic_ranking_score(s, sem)

        # Filter by valid duration constraints
        valid_segments = [
            s
            for s in segments
            if self.min_duration <= s.duration <= self.max_duration
        ]

        # If strict duration filter returned empty, fallback to all segments
        if not valid_segments:
            valid_segments = segments

        # Sort strictly descending by composite engagement score
        sorted_segments = sorted(valid_segments, key=lambda s: s.composite_score, reverse=True)

        selected: List[SegmentAnalysis] = []

        for candidate in sorted_segments:
            if len(selected) >= top_n:
                break

            # Check overlap against already chosen clips
            is_redundant = False
            for chosen in selected:
                iou = self.calculate_temporal_iou(
                    candidate.start_time,
                    candidate.end_time,
                    chosen.start_time,
                    chosen.end_time,
                )
                if iou > self.max_overlap_iou:
                    is_redundant = True
                    break

            if not is_redundant:
                selected.append(candidate)

        logger.info(
            f"Selected {len(selected)} unique non-redundant highlights from {len(segments)} candidate windows."
        )
        return selected



highlight_ranker = HighlightRanker()
