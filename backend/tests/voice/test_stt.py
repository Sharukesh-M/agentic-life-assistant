"""
Unit and Integration Tests for JARVIX STT Subsystem.
Tests STTInterface, WhisperSTT, and MockSTT engines.
"""

import os
import sys
import unittest

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.voice.stt_interface import STTInterface, STTResult
from app.voice.stt_service import WhisperSTT, MockSTT, get_stt_engine
from tests.voice.fixtures.generate_fixtures import generate_all_fixtures

class TestSTTSubsystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        generate_all_fixtures()
        cls.valid_wav = os.path.join(fixtures_dir, "test_input.wav")
        cls.empty_wav = os.path.join(fixtures_dir, "empty_input.wav")
        cls.nonexistent_wav = os.path.join(fixtures_dir, "nonexistent.wav")

    def test_mock_stt_valid_audio(self):
        engine = MockSTT()
        result = engine.transcribe(self.valid_wav)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.text)
        self.assertIn("JARVIX", result.text)
        self.assertEqual(result.language, "en")
        self.assertGreaterEqual(result.duration_seconds, 0.0)
        self.assertEqual(result.device, "cpu")

    def test_mock_stt_empty_audio(self):
        engine = MockSTT()
        result = engine.transcribe(self.empty_wav)

        self.assertFalse(result.success)
        self.assertIn("empty", result.error_message.lower())

    def test_mock_stt_nonexistent_audio(self):
        engine = MockSTT()
        result = engine.transcribe(self.nonexistent_wav)

        self.assertFalse(result.success)
        self.assertIn("not found", result.error_message.lower())

    def test_stt_factory(self):
        engine = get_stt_engine(force_mock=True)
        self.assertIsInstance(engine, STTInterface)
        self.assertEqual(engine.get_device(), "cpu")

    def test_whisper_device_detection(self):
        stt = WhisperSTT(force_device="cpu")
        device = stt.get_device()
        self.assertIn(device, ["cpu", "mps", "cuda:0"])

if __name__ == "__main__":
    unittest.main()
