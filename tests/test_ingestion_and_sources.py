"""
Unit Tests for Gameplay Ingestion & Source Discovery (Modes A and B)
"""

import os
import unittest
import tempfile
from pathlib import Path
from modules.gameplay_ingestion import GameplayIngestionService
from modules.source_discovery import SourceDiscoveryService


class TestIngestionAndSources(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.ingestion = GameplayIngestionService(input_dir=self.temp_path)
        self.sources = SourceDiscoveryService()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_checksum_computation(self):
        dummy_file = self.temp_path / "dummy.mp4"
        dummy_file.write_bytes(b"GTA_6_TEST_VIDEO_BYTES_12345")

        h1 = self.ingestion.compute_sha256(dummy_file)
        h2 = self.ingestion.compute_sha256(dummy_file)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_unsupported_format_rejection(self):
        txt_file = self.temp_path / "notes.txt"
        txt_file.write_text("not a video")

        with self.assertRaises(ValueError):
            self.ingestion.ingest_video_file(txt_file)

    def test_mode_b_authorized_source_registration(self):
        res = self.sources.register_authorized_source(
            title="Leonida Sunset Drive",
            license_type="CC-BY",
            creator_name="GamerArchive",
            source_url="https://creativecommons.org/licenses/by/4.0/",
        )
        self.assertTrue(res["permission_verified"])
        self.assertEqual(res["license_type"], "CC-BY")

        # Verify illegal license rejection
        with self.assertRaises(ValueError):
            self.sources.register_authorized_source(
                title="Random Stream Rip",
                license_type="All Rights Reserved No Derivative",
                creator_name="RandomStreamer",
            )

    def test_attribution_credit_generation(self):
        res = self.sources.register_authorized_source(
            title="Vice City B-Roll",
            license_type="Rockstar Press Kit Official",
            creator_name="Rockstar Games",
            source_url="https://rockstargames.com/press",
        )
        credit = self.sources.get_attribution_credit(res["source_id"])
        self.assertIn("Rockstar Games", credit)
        self.assertIn("Rockstar Press Kit Official", credit)


if __name__ == "__main__":
    unittest.main()
