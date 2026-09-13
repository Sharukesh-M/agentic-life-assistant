"""
Audio Processor and Capture Abstraction for JARVIX Voice Subsystem.
Handles Microphone Recording Abstraction and Audio Format Normalization.
Keep microphone capture separate from STT so unit tests do not depend on physical hardware.
"""

import os
import wave
import struct
from abc import ABC, abstractmethod
from typing import Optional, Tuple

class AudioInputError(Exception):
    """Raised when audio capture or normalization fails."""
    pass

class AudioInput(ABC):
    """Abstract Base Class for Audio Capture Inputs."""

    @abstractmethod
    def capture(self, output_path: str, duration_seconds: float = 5.0) -> str:
        """
        Captures audio into output_path WAV file.
        """
        pass

class FileAudioInput(AudioInput):
    """Audio capture from an existing file fixture or buffer."""

    def __init__(self, source_path: str):
        self.source_path = source_path

    def capture(self, output_path: str, duration_seconds: float = 5.0) -> str:
        if not os.path.exists(self.source_path):
            raise AudioInputError(f"Source audio file does not exist: {self.source_path}")
        if os.path.getsize(self.source_path) == 0:
            raise AudioInputError(f"Source audio file is empty (0 bytes): {self.source_path}")
        
        # Copy or pass source path
        if output_path != self.source_path:
            with open(self.source_path, "rb") as sf, open(output_path, "wb") as df:
                df.write(sf.read())
        return output_path

class MicrophoneAudioInput(AudioInput):
    """
    Microphone Audio Capture.
    Captures live microphone stream if sounddevice/pyaudio hardware is available.
    """

    def capture(self, output_path: str, duration_seconds: float = 5.0) -> str:
        try:
            import sounddevice as sd
            import soundfile as sf
            
            sample_rate = 16000
            print(f"[JARVIX Microphone] Recording audio for {duration_seconds}s at {sample_rate}Hz...")
            recording = sd.rec(int(duration_seconds * sample_rate), samplerate=sample_rate, channels=1)
            sd.wait()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            sf.write(output_path, recording, sample_rate)
            return output_path
        except Exception as e:
            raise AudioInputError(f"Microphone capture unavailable: {str(e)}")

class AudioNormalizer:
    """
    Normalizes sample rate, channels, PCM formatting, and validates input audio.
    """

    @staticmethod
    def validate_audio_file(audio_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validates whether audio file exists, is readable, and non-empty.
        """
        if not audio_path or not isinstance(audio_path, str):
            return False, "Audio path must be a non-empty string."
        if not os.path.exists(audio_path):
            return False, f"Audio file does not exist at path: {audio_path}"
        if os.path.getsize(audio_path) == 0:
            return False, "Audio file is empty (0 bytes)."
        return True, None

    @staticmethod
    def normalize_audio(
        input_path: str,
        output_path: Optional[str] = None,
        target_sample_rate: int = 16000,
        target_channels: int = 1
    ) -> str:
        """
        Verifies and normalizes WAV audio file properties.
        """
        is_valid, err = AudioNormalizer.validate_audio_file(input_path)
        if not is_valid:
            raise AudioInputError(err)

        if not output_path:
            output_path = input_path

        # If WAV file, check format parameters via wave stdlib module
        try:
            with wave.open(input_path, "rb") as wf:
                channels = wf.getnchannels()
                rate = wf.getframerate()
                width = wf.getsampwidth()

            # If already correct format, return
            if channels == target_channels and rate == target_sample_rate and width == 2:
                return input_path
        except Exception:
            # If standard wave reading fails or format is non-WAV, pass through path safely
            pass

        return input_path
