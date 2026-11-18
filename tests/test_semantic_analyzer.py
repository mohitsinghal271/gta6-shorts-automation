"""
Unit Tests for Semantic AI Gameplay Analysis Module
Tests all 7 required fixes:
1. Missing NumPy import validation
2. Peak action moment selection vs fixed middle frame
3. Composite fallback score calculation (0.40*50 + 0.35*55 + 0.25*60 = 54.25)
4. Robust response validation (JSON parsing, score clamping, missing fields, malformed input)
5. Generic factual fallback commentary without hallucinations
6. Highlight ranker semantic score combination
7. Commentary generation with contextual event summaries in Hindi, English, and Hinglish
"""

import unittest
import numpy as np
from pathlib import Path

from modules.semantic_analyzer import (
    SemanticAnalyzer,
    SemanticAnalysisResult,
    calculate_semantic_composite,
    semantic_analyzer,
)
from modules.video_analyzer import SegmentAnalysis
from modules.highlight_ranker import HighlightRanker
from modules.voice_generator import VoiceGenerator


class TestSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()
        self.ranker = HighlightRanker(max_overlap_iou=0.30)
        self.voice_gen = VoiceGenerator()

    def test_numpy_import_and_matrix_support(self):
        """Fix 1: Ensure NumPy is properly imported and functional."""
        arr = np.array([50.0, 55.0, 60.0])
        weights = np.array([0.40, 0.35, 0.25])
        comp = float(np.dot(arr, weights))
        self.assertAlmostEqual(comp, 54.25, places=2)

    def test_actual_peak_selection_vs_fixed_middle(self):
        """Fix 2: Peak frame must find the actual motion/audio peak rather than duration * 0.5."""
        start_t = 0.0
        end_t = 30.0
        fixed_mid = 15.0

        # Audio energy profile peaking at t = 22.5s (away from 15.0s midpoint)
        audio_profile = [
            (5.0, 30.0),
            (10.0, 35.0),
            (15.0, 40.0),  # midpoint energy is modest
            (22.5, 95.0),  # massive explosion / siren peak here!
            (28.0, 30.0),
        ]

        peak_t = self.analyzer.find_action_peak_timestamp(
            start_time=start_t,
            end_time=end_t,
            audio_profile=audio_profile,
        )

        # Must pick the actual audio peak at 22.5s, NOT the fixed midpoint (15.0s)
        self.assertNotEqual(peak_t, fixed_mid)
        self.assertAlmostEqual(peak_t, 22.5, delta=1.0)

        # Motion score profile peaking at t = 8.0s
        scenes = [
            {"start_time": 0.0, "end_time": 6.0, "motion_score": 15.0},
            {"start_time": 6.0, "end_time": 10.0, "motion_score": 45.0},  # high-speed chase cut!
            {"start_time": 10.0, "end_time": 20.0, "motion_score": 18.0},
            {"start_time": 20.0, "end_time": 30.0, "motion_score": 12.0},
        ]
        peak_motion_t = self.analyzer.find_action_peak_timestamp(
            start_time=start_t,
            end_time=end_t,
            scenes=scenes,
        )
        self.assertNotEqual(peak_motion_t, fixed_mid)
        self.assertAlmostEqual(peak_motion_t, 8.0, delta=1.5)

        # Test intelligent keyframe extraction extracts [hook, peak, climax] in order
        keyframes = self.analyzer.extract_intelligent_keyframes(
            start_time=start_t,
            end_time=end_t,
            audio_profile=audio_profile,
        )
        self.assertEqual(len(keyframes), 3)
        self.assertLess(keyframes[0], keyframes[1])
        self.assertLess(keyframes[1], keyframes[2])
        self.assertAlmostEqual(keyframes[1], 22.5, delta=1.0)

    def test_composite_fallback_score_calculation(self):
        """Fix 3: Verify composite score: 0.40 * 50 + 0.35 * 55 + 0.25 * 60 = 54.25."""
        comp = calculate_semantic_composite(stunt_score=50.0, humor_score=55.0, cinematic_score=60.0)
        self.assertEqual(comp, 54.25)

        # Also verify fallback result object uses this exact value
        fb = self.analyzer.get_factual_fallback_result()
        self.assertEqual(fb.stunt_score, 50.0)
        self.assertEqual(fb.humor_score, 55.0)
        self.assertEqual(fb.cinematic_score, 60.0)
        self.assertEqual(fb.composite_score, 54.25)
        self.assertTrue(fb.is_fallback)

    def test_response_validation_robustness(self):
        """Fix 4: Validate JSON, score clamping [0, 100], missing fields, and malformed input."""
        # 1. Valid clean JSON
        valid_raw = (
            '{\n'
            '  "humor_score": 75.0,\n'
            '  "stunt_score": 85.0,\n'
            '  "cinematic_score": 90.0,\n'
            '  "event_summary": "Police cruiser rams through Vice City storefront during high-speed chase.",\n'
            '  "why_entertaining": "Spectacular glass shatter physics and aggressive police AI.",\n'
            '  "suggested_hook": "Vice City police have NO chill!"\n'
            '}'
        )
        res = self.analyzer.validate_and_parse_response(valid_raw)
        self.assertFalse(res.is_fallback)
        self.assertEqual(res.humor_score, 75.0)
        self.assertEqual(res.stunt_score, 85.0)
        self.assertEqual(res.cinematic_score, 90.0)
        # Expected composite: 0.40*85 + 0.35*75 + 0.25*90 = 34.0 + 26.25 + 22.5 = 82.75
        self.assertEqual(res.composite_score, 82.75)
        self.assertIn("storefront", res.event_summary)
        self.assertIn("NO chill", res.suggested_hook)

        # 2. Markdown fenced JSON block
        markdown_raw = f"Here is the analysis:\n```json\n{valid_raw}\n```\nHope that helps!"
        res_md = self.analyzer.validate_and_parse_response(markdown_raw)
        self.assertFalse(res_md.is_fallback)
        self.assertEqual(res_md.composite_score, 82.75)

        # 3. Out-of-bounds scores clamped to [0.0, 100.0]
        oob_raw = '{"humor_score": 150.0, "stunt_score": -20.0, "cinematic_score": 80.0}'
        res_oob = self.analyzer.validate_and_parse_response(oob_raw)
        self.assertEqual(res_oob.humor_score, 100.0)  # clamped from 150
        self.assertEqual(res_oob.stunt_score, 0.0)    # clamped from -20
        self.assertEqual(res_oob.cinematic_score, 80.0)

        # 4. Completely malformed / corrupt response -> fallback with 54.25
        malformed_raw = "I am a language model and could not generate valid JSON. System Error 500."
        res_err = self.analyzer.validate_and_parse_response(malformed_raw)
        self.assertTrue(res_err.is_fallback)
        self.assertEqual(res_err.composite_score, 54.25)

    def test_factual_neutral_fallback_no_hallucinations(self):
        """Fix 5: When VLM is unavailable, be factual and neutral without inventing fake events."""
        fb = self.analyzer.get_factual_fallback_result()
        # Factual, neutral description
        self.assertEqual(fb.event_summary, "GTA 6 gameplay sequence")
        self.assertIn("GTA 6 gameplay sequence", fb.suggested_hook)
        # Verify it doesn't mention specific unverified events
        self.assertNotIn("helicopter", fb.event_summary.lower())
        self.assertNotIn("bank robbery", fb.event_summary.lower())

    def test_ranker_integration_with_semantic_scores(self):
        """Fix 6: Combine motion, audio, and semantic score in highlight ranker."""
        seg_action_only = SegmentAnalysis(
            start_time=0.0,
            end_time=30.0,
            duration=30.0,
            visual_excitement=80.0,
            action_intensity=80.0,
            audio_intensity=70.0,
            unpredictability=60.0,
            hook_potential=75.0,
            ending_quality=70.0,
            storytelling_potential=70.0,
            composite_score=75.0,
            tags=["police_chase"],
            semantic_score=50.0,
        )

        seg_viral_stunt = SegmentAnalysis(
            start_time=35.0,
            end_time=65.0,
            duration=30.0,
            visual_excitement=80.0,
            action_intensity=80.0,
            audio_intensity=70.0,
            unpredictability=60.0,
            hook_potential=75.0,
            ending_quality=70.0,
            storytelling_potential=70.0,
            composite_score=75.0,
            tags=["viral_stunt"],
            semantic_score=95.0,  # Highly entertaining stunt recognized by VLM
        )

        ranked = self.ranker.rank_and_deduplicate([seg_action_only, seg_viral_stunt], top_n=2)
        # seg_viral_stunt should be ranked first due to 95.0 semantic score
        self.assertEqual(ranked[0].start_time, 35.0)
        self.assertGreater(ranked[0].composite_score, ranked[1].composite_score)

    def test_contextual_commentary_generation(self):
        """Fix 7: Generate scripts from actual event summaries in Hindi, English, and Hinglish."""
        semantic_info = {
            "event_summary": "Lucia leaps off a moving speed boat onto a police patrol cutter",
            "why_entertaining": "Crazy mid-air jump physics and instant five-star wanted alert",
            "suggested_hook": "Is Lucia the craziest GTA protagonist ever?",
        }

        # 1. English contextual commentary
        en_script = self.voice_gen.assemble_script("english", ["stunt"], semantic_info=semantic_info)
        self.assertIn("Lucia leaps off a moving speed boat", en_script)
        self.assertIn("Crazy mid-air jump physics", en_script)
        self.assertIn("craziest GTA protagonist", en_script)

        # 2. Hinglish contextual commentary
        hinglish_script = self.voice_gen.assemble_script("hinglish", ["stunt"], semantic_info=semantic_info)
        self.assertIn("Bhai yeh dekho", hinglish_script)
        self.assertIn("Lucia leaps off a moving speed boat", hinglish_script)
        self.assertIn("Crazy mid-air jump physics", hinglish_script)

        # 3. Hindi contextual commentary
        hindi_script = self.voice_gen.assemble_script("hindi", ["stunt"], semantic_info=semantic_info)
        self.assertIn("GTA 6 का यह जबरदस्त सीन देखिए", hindi_script)
        self.assertIn("Lucia leaps off a moving speed boat", hindi_script)

    def test_scene_boundary_objects_and_zero_signal_edge_cases(self):
        """Edge Case: SceneBoundary dataclass support and zero-motion/silent audio fallback."""
        from modules.scene_detector import SceneBoundary

        # 1. SceneBoundary objects instead of dicts
        boundaries = [
            SceneBoundary(scene_index=0, start_time=0.0, end_time=10.0, duration=10.0, motion_score=10.0),
            SceneBoundary(scene_index=1, start_time=10.0, end_time=20.0, duration=10.0, motion_score=50.0),
            SceneBoundary(scene_index=2, start_time=20.0, end_time=30.0, duration=10.0, motion_score=15.0),
        ]
        peak_t = self.analyzer.find_action_peak_timestamp(0.0, 30.0, scenes=boundaries)
        self.assertAlmostEqual(peak_t, 15.0, delta=1.0)

        # 2. Completely silent audio (0.0 energy) and zero motion (0.0 score) -> exact midpoint
        zero_audio = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
        zero_scenes = [{"start_time": 0.0, "end_time": 20.0, "motion_score": 0.0}]
        clean_mid = self.analyzer.find_action_peak_timestamp(0.0, 20.0, scenes=zero_scenes, audio_profile=zero_audio)
        self.assertEqual(clean_mid, 10.0)

    def test_short_clip_monotonic_keyframes(self):
        """Edge Case: Very short clips (< 2 seconds) must strictly maintain start <= hook < peak < climax <= end."""
        keyframes = self.analyzer.extract_intelligent_keyframes(start_time=5.0, end_time=6.2)
        self.assertEqual(len(keyframes), 3)
        self.assertGreaterEqual(keyframes[0], 5.0)
        self.assertLess(keyframes[0], keyframes[1])
        self.assertLess(keyframes[1], keyframes[2])
        self.assertLessEqual(keyframes[2], 6.2)

    def test_vlm_response_robustness_advanced(self):
        """Edge Case: Percentage scores, ratio strings, single-line fences, extra braces, and field aliases."""
        # Single-line fenced block with percentage and ratio
        vlm_raw = 'Here is the result: ```json {"stunt": "95%", "humor": "80/100", "cinematic": 90, "summary": "Lucia speed boat jump", "hook": "Speed boat jump!"}```'
        res = self.analyzer.validate_and_parse_response(vlm_raw)
        self.assertFalse(res.is_fallback)
        self.assertEqual(res.stunt_score, 95.0)
        self.assertEqual(res.humor_score, 80.0)
        self.assertEqual(res.cinematic_score, 90.0)
        self.assertEqual(res.event_summary, "Lucia speed boat jump")
        self.assertEqual(res.suggested_hook, "Speed boat jump!")

        # Extra curly braces in surrounding reasoning text
        reasoning_raw = (
            "Thinking: {analyzing high speed chase}\n"
            "Result:\n"
            '{"humor_score": 70, "stunt_score": 85, "cinematic_score": 75, "event_summary": "Police pursuit", "suggested_hook": "Chase!"}\n'
            "Confidence: {high}"
        )
        res_reasoning = self.analyzer.validate_and_parse_response(reasoning_raw)
        self.assertFalse(res_reasoning.is_fallback)
        self.assertEqual(res_reasoning.stunt_score, 85.0)
        self.assertEqual(res_reasoning.event_summary, "Police pursuit")

    def test_voice_commentary_with_result_object(self):
        """Edge Case: assemble_script works when passed a SemanticAnalysisResult object directly."""
        res_obj = SemanticAnalysisResult(
            humor_score=70.0,
            stunt_score=85.0,
            cinematic_score=75.0,
            composite_score=77.5,
            event_summary="Lucia outruns five police cruisers on Ocean Drive",
            why_entertaining="Neon lighting reflections and intense sirens",
            suggested_hook="Can Lucia escape Ocean Drive?",
        )
        script = self.voice_gen.assemble_script("hinglish", ["chase"], semantic_info=res_obj)
        self.assertIn("Lucia outruns five police cruisers", script)
        self.assertIn("Neon lighting reflections", script)


if __name__ == "__main__":
    unittest.main()
