"""
Integration Tests for JARVIX Voice API Endpoints.
Tests /api/voice/transcribe, /api/voice/tts, and /api/voice/chat endpoints.
Directly tests endpoint logic with fallback for environments where httpx/TestClient is not installed.
"""

import os
import sys
import asyncio
import unittest

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False

from app.voice.tts_router import (
    transcribe_speech, synthesize_speech, voice_chat_endpoint,
    TranscribeRequest, TTSRequest, VoiceChatRequest
)
from tests.voice.fixtures.generate_fixtures import generate_all_fixtures

class TestVoiceAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        generate_all_fixtures()
        cls.valid_wav = os.path.join(fixtures_dir, "test_input.wav")
        if HAS_TESTCLIENT:
            cls.client = TestClient(app)
        else:
            cls.client = None

    def test_transcribe_endpoint(self):
        if self.client:
            payload = {"audio_path": self.valid_wav, "language": "en"}
            response = self.client.post("/api/voice/transcribe", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("JARVIX", data["transcript"])
        else:
            req = TranscribeRequest(audio_path=self.valid_wav, language="en")
            res = asyncio.run(transcribe_speech(req))
            self.assertEqual(res.status, "success")
            self.assertIn("JARVIX", res.transcript)

    def test_tts_endpoint(self):
        if self.client:
            payload = {"text": "Hello from API test.", "output_filename": "api_test_tts.wav"}
            response = self.client.post("/api/voice/tts", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertTrue(os.path.exists(data["audio_path"]))
        else:
            req = TTSRequest(text="Hello from API test.", output_filename="api_test_tts.wav")
            res = asyncio.run(synthesize_speech(req))
            self.assertEqual(res.status, "success")
            self.assertTrue(os.path.exists(res.audio_path))

    def test_voice_chat_endpoint(self):
        if self.client:
            payload = {
                "audio_path": self.valid_wav,
                "user_id": "api_test_user",
                "output_filename": "api_test_chat.wav"
            }
            response = self.client.post("/api/voice/chat", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("JARVIX", data["transcript"])
            self.assertIsNotNone(data["response_text"])
            self.assertTrue(os.path.exists(data["audio"]))
            self.assertIsNotNone(data["latency"].total_seconds)
        else:
            req = VoiceChatRequest(audio_path=self.valid_wav, user_id="api_test_user", output_filename="api_test_chat.wav")
            res = asyncio.run(voice_chat_endpoint(req, db=None))
            self.assertEqual(res.status, "success")
            self.assertIn("JARVIX", res.transcript)
            self.assertIsNotNone(res.response_text)
            self.assertTrue(os.path.exists(res.audio))
            self.assertIsNotNone(res.latency.total_seconds)

if __name__ == "__main__":
    unittest.main()
