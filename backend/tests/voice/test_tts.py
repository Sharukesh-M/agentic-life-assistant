"""
Unit and Integration Tests for JARVIX TTS Subsystem.
Tests TTSInterface, OmniVoiceTTS, and MockTTS engines.
"""

import os
import sys
import wave
import unittest

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.voice.tts_interface import TTSInterface, TTSResult
from app.voice.omnivoice_service import OmniVoiceTTS, MockTTS, get_tts_engine

class TestTTSSubsystem(unittest.TestCase):

    def setUp(self):
        self.output_dir = os.path.join("outputs", "audio")
        os.makedirs(self.output_dir, exist_ok=True)
        self.target_wav = os.path.join(self.output_dir, "test_tts_unit_output.wav")

    def tearDown(self):
        if os.path.exists(self.target_wav):
            try:
                os.remove(self.target_wav)
            except Exception:
                pass

    def test_mock_tts_valid_text(self):
        engine = MockTTS()
        test_text = "Hello, I am JARVIX. Voice synthesis is working successfully."
        result = engine.synthesize(test_text, output_path=self.target_wav)

        self.assertTrue(result.success)
        self.assertTrue(os.path.exists(self.target_wav))
        self.assertGreater(os.path.getsize(self.target_wav), 0)

        # Validate WAV headers
        with wave.open(self.target_wav, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getframerate(), 16000)
            self.assertGreater(wf.getnframes(), 0)

        self.assertGreater(result.duration_seconds, 0.0)
        self.assertEqual(result.text, test_text)

    def test_mock_tts_empty_text(self):
        engine = MockTTS()
        result = engine.synthesize("", output_path=self.target_wav)

        self.assertFalse(result.success)
        self.assertIn("empty", result.error_message.lower())

    def test_tts_factory(self):
        engine = get_tts_engine(force_mock=True)
        self.assertIsInstance(engine, TTSInterface)
        self.assertEqual(engine.get_device(), "cpu")

if __name__ == "__main__":
    unittest.main()
