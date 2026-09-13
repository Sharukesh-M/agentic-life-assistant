"""
OmniVoice TTS Implementation for JARVIX.
Uses k2-fsa/OmniVoice with device auto-detection and singleton model caching.
"""

import os
import time
try:
    import psutil
except ImportError:
    psutil = None
from typing import Optional
from .tts_interface import TTSInterface, TTSResult

class OmniVoiceTTS(TTSInterface):
    """
    OmniVoice TTS Service Implementation.
    Loads k2-fsa/OmniVoice model once and reuses it for synthesis requests.
    """
    
    _instance: Optional['OmniVoiceTTS'] = None
    _model = None
    _device: str = "cpu"
    _model_load_time: float = 0.0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(OmniVoiceTTS, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "k2-fsa/OmniVoice", force_device: Optional[str] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.model_name = model_name
        self._device = force_device or self._detect_hardware_device()
        self._initialized = True
        self._load_model()

    def _detect_hardware_device(self) -> str:
        """
        Auto-detects optimal available hardware device (cuda -> mps -> cpu).
        Does NOT hardcode cuda:0 or mps unless hardware support exists.
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
        """
        Loads the OmniVoice model once into memory on the detected hardware device.
        """
        if OmniVoiceTTS._model is not None:
            return

        start_time = time.time()
        try:
            from omnivoice import OmniVoice
            print(f"[JARVIX Voice] Loading OmniVoice model '{self.model_name}' on device '{self._device}'...")
            OmniVoiceTTS._model = OmniVoice.from_pretrained(self.model_name)
            if hasattr(OmniVoiceTTS._model, "to"):
                OmniVoiceTTS._model.to(self._device)
            OmniVoiceTTS._model_load_time = time.time() - start_time
            print(f"[JARVIX Voice] Model loaded successfully in {OmniVoiceTTS._model_load_time:.2f}s.")
        except Exception as e:
            OmniVoiceTTS._model_load_time = time.time() - start_time
            print(f"[JARVIX Voice Error] Failed to load OmniVoice model: {str(e)}")
            OmniVoiceTTS._model = None

    def get_device(self) -> str:
        return self._device

    def synthesize(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        """
        Synthesize text into speech WAV using OmniVoice.
        """
        if not output_path:
            os.makedirs(os.path.join("outputs", "audio"), exist_ok=True)
            output_path = os.path.join("outputs", "audio", "jarvix_tts_output.wav")

        if OmniVoiceTTS._model is None:
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_seconds=0.0,
                device=self._device,
                load_time_seconds=OmniVoiceTTS._model_load_time,
                generation_time_seconds=0.0,
                real_time_factor=0.0,
                success=False,
                error_message="OmniVoice model is not loaded. Check installation and dependencies."
            )

        start_time = time.time()
        try:
            # Generate speech audio
            # OmniVoice API expects text and outputs audio tensor/file
            audio_data = OmniVoiceTTS._model.generate(text)
            gen_time = time.time() - start_time
            
            # Save output WAV file
            if hasattr(audio_data, "save"):
                audio_data.save(output_path)
            elif hasattr(OmniVoiceTTS._model, "save_audio"):
                OmniVoiceTTS._model.save_audio(audio_data, output_path)
            else:
                import soundfile as sf
                sf.write(output_path, audio_data, 24000)

            duration = len(audio_data) / 24000.0 if hasattr(audio_data, "__len__") else 2.0
            rtf = gen_time / duration if duration > 0 else 0.0

            # RAM usage check
            if psutil:
                process = psutil.Process(os.getpid())
                ram_mb = process.memory_info().rss / (1024 * 1024)
            else:
                ram_mb = 0.0

            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_seconds=duration,
                device=self._device,
                load_time_seconds=OmniVoiceTTS._model_load_time,
                generation_time_seconds=gen_time,
                real_time_factor=rtf,
                metadata={"ram_usage_mb": ram_mb},
                success=True
            )
        except Exception as e:
            gen_time = time.time() - start_time
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_seconds=0.0,
                device=self._device,
                load_time_seconds=OmniVoiceTTS._model_load_time,
                generation_time_seconds=gen_time,
                real_time_factor=0.0,
                success=False,
                error_message=f"TTS Generation error: {str(e)}"
            )


class MockTTS(TTSInterface):
    """
    Deterministic Mock/Fallback TTS Engine for testing and environments where OmniVoice is unconfigured.
    Generates real, valid 16kHz PCM WAV audio files with synthetic audio tones.
    """

    def get_device(self) -> str:
        return "cpu"

    def synthesize(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        start_time = time.time()

        if not text or not text.strip():
            return TTSResult(
                audio_path="",
                text=text,
                duration_seconds=0.0,
                device="cpu",
                load_time_seconds=0.0,
                generation_time_seconds=time.time() - start_time,
                real_time_factor=0.0,
                success=False,
                error_message="Text field cannot be empty."
            )

        if not output_path:
            os.makedirs(os.path.join("outputs", "audio"), exist_ok=True)
            output_path = os.path.join("outputs", "audio", "jarvix_tts_output.wav")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Estimate duration based on text length (~0.06s per character, min 1.5s)
        duration = max(1.5, len(text) * 0.06)
        sample_rate = 16000
        n_samples = int(sample_rate * duration)

        import wave
        import struct
        import math

        try:
            with wave.open(output_path, "wb") as f:
                f.setnchannels(1)       # Mono
                f.setsampwidth(2)      # 16-bit PCM
                f.setframerate(sample_rate)
                freq = 440.0
                for i in range(n_samples):
                    val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * freq * i / sample_rate))
                    f.writeframes(struct.pack("<h", val))

            gen_time = time.time() - start_time
            rtf = gen_time / duration if duration > 0 else 0.0

            ram_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024) if psutil else 0.0

            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_seconds=duration,
                device="cpu",
                load_time_seconds=0.0,
                generation_time_seconds=gen_time,
                real_time_factor=rtf,
                metadata={"engine": "MockTTS", "ram_usage_mb": ram_mb},
                success=True
            )
        except Exception as e:
            return TTSResult(
                audio_path=output_path,
                text=text,
                duration_seconds=0.0,
                device="cpu",
                load_time_seconds=0.0,
                generation_time_seconds=time.time() - start_time,
                real_time_factor=0.0,
                success=False,
                error_message=f"MockTTS synthesis failed: {str(e)}"
            )


def get_tts_engine(model_name: str = "k2-fsa/OmniVoice", force_mock: bool = False) -> TTSInterface:
    """
    Factory function for TTS engine. Returns OmniVoiceTTS if loaded,
    otherwise falls back cleanly to MockTTS.
    """
    if force_mock:
        return MockTTS()

    try:
        import omnivoice
        engine = OmniVoiceTTS(model_name=model_name)
        if OmniVoiceTTS._model is not None:
            return engine
        return MockTTS()
    except Exception:
        return MockTTS()

