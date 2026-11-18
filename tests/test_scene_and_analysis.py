"""
Unit Tests for Scene Analysis and Highlight Ranking
"""

import unittest
from modules.video_analyzer import SegmentAnalysis
from modules.highlight_ranker import HighlightRanker


class TestSceneAndAnalysis(unittest.TestCase):
    def setUp(self):
        self.ranker = HighlightRanker(max_overlap_iou=0.30)

    def test_temporal_iou_calculation(self):
        # Exact match -> 1.0
        self.assertAlmostEqual(self.ranker.calculate_temporal_iou(0.0, 30.0, 0.0, 30.0), 1.0)
        # Disjoint windows -> 0.0
        self.assertAlmostEqual(self.ranker.calculate_temporal_iou(0.0, 30.0, 30.0, 60.0), 0.0)
        # 50% overlap: [0, 30] and [15, 45] -> intersection=15, union=45 -> 15/45 = 0.333
        self.assertAlmostEqual(
            self.ranker.calculate_temporal_iou(0.0, 30.0, 15.0, 45.0), 15.0 / 45.0, places=2
        )

    def test_highlight_ranking_and_deduplication(self):
        segments = [
            SegmentAnalysis(
                start_time=0.0,
                end_time=30.0,
                duration=30.0,
                visual_excitement=80.0,
                action_intensity=85.0,
                audio_intensity=75.0,
                unpredictability=70.0,
                hook_potential=90.0,
                ending_quality=80.0,
                storytelling_potential=80.0,
                composite_score=85.0,
                tags=["high_speed_chase"],
            ),
            # Heavily overlapping candidate with lower score (should be suppressed by NMS)
            SegmentAnalysis(
                start_time=5.0,
                end_time=35.0,
                duration=30.0,
                visual_excitement=75.0,
                action_intensity=80.0,
                audio_intensity=70.0,
                unpredictability=65.0,
                hook_potential=85.0,
                ending_quality=75.0,
                storytelling_potential=75.0,
                composite_score=80.0,
                tags=["police_action"],
            ),
            # Distinct second window with high score
            SegmentAnalysis(
                start_time=40.0,
                end_time=70.0,
                duration=30.0,
                visual_excitement=90.0,
                action_intensity=95.0,
                audio_intensity=85.0,
                unpredictability=80.0,
                hook_potential=92.0,
                ending_quality=85.0,
                storytelling_potential=85.0,
                composite_score=92.0,
                tags=["car_crash_explosion"],
            ),
        ]

        ranked = self.ranker.rank_and_deduplicate(segments, top_n=2)
        self.assertEqual(len(ranked), 2)
        # Highest score candidate (92.0) should be first
        self.assertEqual(ranked[0].start_time, 40.0)
        self.assertEqual(ranked[0].composite_score, 92.0)
        # Second selected should be the 0.0-30.0 segment, suppressing the overlapping 5.0-35.0 segment
        self.assertEqual(ranked[1].start_time, 0.0)
        self.assertEqual(ranked[1].composite_score, 85.0)

    def test_semantic_ranking_boost(self):
        # Two non-overlapping segments with identical motion/audio but different semantic scores
        seg1 = SegmentAnalysis(
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            visual_excitement=70.0,
            action_intensity=70.0,
            audio_intensity=70.0,
            unpredictability=70.0,
            hook_potential=70.0,
            ending_quality=70.0,
            storytelling_potential=70.0,
            composite_score=70.0,
            tags=["action"],
            semantic_score=50.0,
        )
        seg2 = SegmentAnalysis(
            start_time=40.0,
            end_time=70.0,
            duration=30.0,
            visual_excitement=70.0,
            action_intensity=70.0,
            audio_intensity=70.0,
            unpredictability=70.0,
            hook_potential=70.0,
            ending_quality=70.0,
            storytelling_potential=70.0,
            composite_score=70.0,
            tags=["stunt"],
            semantic_score=95.0,  # High semantic score (crazy stunt + humor)
        )

        ranked = self.ranker.rank_and_deduplicate([seg1, seg2], top_n=2)
        # seg2 should be ranked higher due to semantic boost
        self.assertEqual(ranked[0].start_time, 40.0)
        self.assertGreater(ranked[0].composite_score, ranked[1].composite_score)



if __name__ == "__main__":
    unittest.main()
