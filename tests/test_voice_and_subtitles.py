"""
Unit Tests for Voice Generator and Subtitle Generator
"""

import unittest
import tempfile
from pathlib import Path
from modules.voice_generator import VoiceGenerator, TimedWord
from modules.subtitle_generator import SubtitleGenerator


class TestVoiceAndSubtitles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.voice_gen = VoiceGenerator(output_dir=self.temp_path)
        self.sub_gen = SubtitleGenerator(output_dir=self.temp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_script_assembly_languages(self):
        # Hindi
        hi_script = self.voice_gen.assemble_script("hindi", ["chase"])
        self.assertIn("GTA 6", hi_script)
        self.assertIn("पुलिस", hi_script)

        # English
        en_script = self.voice_gen.assemble_script("english", ["crash"])
        self.assertIn("crash physics", en_script)

        # Hinglish
        hinglish_script = self.voice_gen.assemble_script("hinglish", ["chase"])
        self.assertIn("Bhai", hinglish_script)
        self.assertIn("GTA 6", hinglish_script)

    def test_gameplay_only_silent_mode(self):
        res = self.voice_gen.generate_voiceover(
            clip_id=99,
            language="english",
            include_voiceover=False,
        )
        self.assertTrue(res.is_silent)
        self.assertIsNone(res.audio_path)
        self.assertEqual(res.duration, 0.0)

    def test_srt_generation(self):
        words = [
            TimedWord(word="GTA", start=0.0, end=0.4),
            TimedWord(word="6", start=0.4, end=0.7),
            TimedWord(word="police", start=0.7, end=1.2),
            TimedWord(word="chase", start=1.2, end=1.8),
        ]
        srt_file = self.sub_gen.generate_srt(words, clip_id=1, words_per_chunk=2)
        self.assertTrue(srt_file.exists())
        content = srt_file.read_text(encoding="utf-8")
        self.assertIn("00:00:00,000 --> 00:00:00,700", content)
        self.assertIn("GTA 6", content)

    def test_ass_karaoke_generation(self):
        words = [
            TimedWord(word="वाइस", start=0.0, end=0.5),
            TimedWord(word="सिटी", start=0.5, end=1.0),
            TimedWord(word="गेमप्ले", start=1.0, end=1.6),
        ]
        ass_file = self.sub_gen.generate_ass_karaoke(words, clip_id=2, words_per_group=3)
        self.assertTrue(ass_file.exists())
        content = ass_file.read_text(encoding="utf-8")
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResY: 1920", content)
        # Verify karaoke highlighting tag and Devanagari text
        self.assertIn(r"\c&H0000FFFF&", content)
        self.assertIn("वाइस", content)


if __name__ == "__main__":
    unittest.main()
