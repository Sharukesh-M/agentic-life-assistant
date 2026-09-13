"""
Speech-to-Text (STT) Implementation for JARVIX.
Includes WhisperSTT (local PyTorch Whisper engine with hardware auto-detection)
and MockSTT (deterministic fallback/test engine for sandbox environments).
"""

import os
import time
from typing import Optional, Dict, Any
from app.voice.stt_interface import STTInterface, STTResult

class WhisperSTT(STTInterface):
    """
    Local Whisper STT Engine implementation.
    Loads Whisper model once on detected hardware (cuda -> mps -> cpu)
    and reuses it across transcription requests.
    """

    _instance: Optional['WhisperSTT'] = None
    _model = None
    _device: str = "cpu"
    _model_load_time: float = 0.0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WhisperSTT, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "base", force_device: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model_name = model_name
        self._device = force_device or self._detect_hardware_device()
        self._initialized = True
        self._load_model()

    def _detect_hardware_device(self) -> str:
        """
        Auto-detects available hardware device (cuda -> mps -> cpu).
        Does NOT hardcode cuda:0 or mps unless supported by runtime.
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda:0"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        except Exception:
            return "cpu"

    def _load_model(self):
        if WhisperSTT._model is not None:
            return

        start_time = time.time()
        try:
            import whisper
            print(f"[JARVIX STT] Loading Whisper model '{self.model_name}' on device '{self._device}'...")
            WhisperSTT._model = whisper.load_model(self.model_name, device=self._device)
            WhisperSTT._model_load_time = time.time() - start_time
            print(f"[JARVIX STT] Whisper model loaded successfully in {WhisperSTT._model_load_time:.2f}s.")
        except Exception as e:
            WhisperSTT._model_load_time = time.time() - start_time
            print(f"[JARVIX STT Warning] Could not load Whisper model: {str(e)}")
            WhisperSTT._model = None

    def get_device(self) -> str:
        return self._device

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> STTResult:
        """
        Transcribe audio file using Whisper.
        """
        if not os.path.exists(audio_path):
            return STTResult(
                text="",
                device=self._device,
                success=False,
                error_message=f"Audio file not found: {audio_path}"
            )

        if os.path.getsize(audio_path) == 0:
            return STTResult(
                text="",
                device=self._device,
                success=False,
                error_message="Audio file is empty (0 bytes)."
            )

        if WhisperSTT._model is None:
            return STTResult(
                text="",
                device=self._device,
                success=False,
                error_message="Whisper model is not loaded. Ensure 'whisper' and 'torch' packages are installed."
            )

        start_time = time.time()
        try:
            options: Dict[str, Any] = {}
            if language:
                options["language"] = language

            result = WhisperSTT._model.transcribe(audio_path, **options)
            inference_time = time.time() - start_time
            text = result.get("text", "").strip()
            detected_lang = result.get("language", language or "en")

            return STTResult(
                text=text,
                language=detected_lang,
                confidence=1.0,
                duration_seconds=result.get("duration", 0.0),
                device=self._device,
                inference_time_seconds=inference_time,
                metadata={"segments_count": len(result.get("segments", []))},
                success=True
            )
        except Exception as e:
            return STTResult(
                text="",
                device=self._device,
                inference_time_seconds=time.time() - start_time,
                success=False,
                error_message=f"Whisper STT transcription failed: {str(e)}"
            )


class MockSTT(STTInterface):
    """
    Deterministic Mock/Fallback STT Engine for testing and sandbox environments.
    Reads companion text files if present or returns standard transcripts.
    """

    def __init__(self, default_text: Optional[str] = None):
        self.default_text = default_text or "Hello JARVIX, what can you help me with?"

    def get_device(self) -> str:
        return "cpu"

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> STTResult:
        if not os.path.exists(audio_path):
            return STTResult(
                text="",
                device="cpu",
                success=False,
                error_message=f"Audio file not found: {audio_path}"
            )

        if os.path.getsize(audio_path) == 0:
            return STTResult(
                text="",
                device="cpu",
                success=False,
                error_message="Input audio file is empty (0 bytes)."
            )

        start_time = time.time()

        # Check for companion transcript file (e.g. test_input.wav.txt)
        txt_path = f"{audio_path}.txt"
        if os.path.exists(txt_path):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    transcript = f.read().strip()
            except Exception:
                transcript = self.default_text
        else:
            transcript = self.default_text

        inference_time = time.time() - start_time

        return STTResult(
            text=transcript,
            language=language or "en",
            confidence=0.99,
            duration_seconds=2.0,
            device="cpu",
            inference_time_seconds=inference_time,
            metadata={"engine": "MockSTT"},
            success=True
        )


def get_stt_engine(model_name: str = "base", force_mock: bool = False) -> STTInterface:
    """
    Factory function for STT engine. Returns WhisperSTT if available,
    otherwise falls back cleanly to MockSTT.
    """
    if force_mock:
        return MockSTT()

    try:
        import whisper
        import torch
        engine = WhisperSTT(model_name=model_name)
        if WhisperSTT._model is not None:
            return engine
        return MockSTT()
    except Exception:
        return MockSTT()
