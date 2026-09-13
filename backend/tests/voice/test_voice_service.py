"""
End-to-End Orchestration & Integration Tests for JARVIX Voice Service.
Verifies Audio -> STT -> JARVIX Orchestrator -> Response -> TTS -> Audio Output WAV.
Tests Safety Confirmation Gates, Error Recovery, and Mock/Real Execution Paths.
"""

import os
import sys
import wave
import unittest

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.voice.voice_service import VoiceService
from app.voice.stt_service import MockSTT, WhisperSTT
from app.voice.omnivoice_service import MockTTS, OmniVoiceTTS
from app.agent.orchestrator import JARVIXOrchestrator
from tests.voice.fixtures.generate_fixtures import generate_all_fixtures

class TestVoiceServiceOrchestration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        generate_all_fixtures()
        cls.valid_wav = os.path.join(fixtures_dir, "test_input.wav")
        cls.planning_wav = os.path.join(fixtures_dir, "test_planning.wav")
        cls.safety_wav = os.path.join(fixtures_dir, "test_safety.wav")
        cls.empty_wav = os.path.join(fixtures_dir, "empty_input.wav")

    def setUp(self):
        self.stt = MockSTT()
        self.tts = MockTTS()
        self.orchestrator = JARVIXOrchestrator()
        self.service = VoiceService(stt_engine=self.stt, tts_engine=self.tts, orchestrator=self.orchestrator)
        self.output_audio = os.path.join("outputs", "audio", "test_voice_chat_output.wav")

    def tearDown(self):
        if os.path.exists(self.output_audio):
            try:
                os.remove(self.output_audio)
            except Exception:
                pass

    def test_mock_end_to_end_general_conversation(self):
        """Phase 25: Mock end-to-end voice pipeline test for general query."""
        res = self.service.process_audio_chat(
            audio_path=self.valid_wav,
            user_id="test_user",
            output_filename="test_voice_chat_output.wav"
        )

        self.assertEqual(res["status"], "success")
        self.assertIn("JARVIX", res["transcript"])
        self.assertIsNotNone(res["response_text"])
        self.assertTrue(os.path.exists(res["audio_path"]))
        self.assertGreater(os.path.getsize(res["audio_path"]), 0)
        self.assertIn("total_seconds", res["latency"])

    def test_mock_end_to_end_planning(self):
        """Phase 25: Mock end-to-end voice pipeline test for planning request."""
        res = self.service.process_audio_chat(
            audio_path=self.planning_wav,
            user_id="test_user",
            output_filename="test_voice_chat_output.wav"
        )

        self.assertEqual(res["status"], "success")
        self.assertIn("Python", res["transcript"])
        self.assertIsNotNone(res["response_text"])
        self.assertTrue(os.path.exists(res["audio_path"]))

    def test_voice_safety_confirmation_gate(self):
        """Phase 16 & 17: High impact action via voice requires confirmation."""
        res = self.service.process_audio_chat(
            audio_path=self.safety_wav,
            user_id="test_user",
            output_filename="test_voice_chat_output.wav"
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["orchestrator_status"], "requires_confirmation")
        self.assertIsNotNone(res["confirmation_prompt"])
        self.assertEqual(res["response_text"], res["confirmation_prompt"])
        self.assertTrue(os.path.exists(res["audio_path"]))

    def test_error_handling_empty_audio(self):
        """Phase 23: Empty audio file returns error safely without claiming success."""
        res = self.service.process_audio_chat(
            audio_path=self.empty_wav,
            user_id="test_user"
        )

        self.assertEqual(res["status"], "error")
        self.assertIn("error", res)
        self.assertEqual(res["audio_path"], "")

    def test_error_handling_invalid_path(self):
        """Phase 23: Nonexistent audio file path returns error safely."""
        res = self.service.process_audio_chat(
            audio_path="invalid/path/file.wav",
            user_id="test_user"
        )

        self.assertEqual(res["status"], "error")
        self.assertIn("does not exist", res["error"])

    def test_real_local_voice_capability_check(self):
        """Phase 26: Diagnostic check for real local STT / TTS package availability."""
        try:
            import whisper
            import torch
            whisper_avail = True
        except ImportError:
            whisper_avail = False

        try:
            import omnivoice
            omnivoice_avail = True
        except ImportError:
            omnivoice_avail = False

        if not whisper_avail:
            print("[JARVIX Test Report] Real STT stage: NOT RUN — dependencies (whisper/torch) unavailable")
        if not omnivoice_avail:
            print("[JARVIX Test Report] Real OmniVoice stage: NOT RUN — dependencies (omnivoice) unavailable")

if __name__ == "__main__":
    unittest.main()
