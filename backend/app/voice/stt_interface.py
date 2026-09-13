"""
Abstract Interface for JARVIX Speech-To-Text (STT) Engine.
Enables pluggable STT implementations (Whisper, faster-whisper, mock/testing, cloud adapters)
without changing higher-level agent, voice orchestration, or API code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class STTResult:
    """
    Standardized Result object returned by any JARVIX STT implementation.
    """
    text: str
    language: Optional[str] = "en"
    confidence: float = 1.0
    duration_seconds: float = 0.0
    device: str = "cpu"
    inference_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None

class STTInterface(ABC):
    """
    Abstract Base Class for JARVIX Speech-to-Text Engine.
    """

    @abstractmethod
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> STTResult:
        """
        Transcribes the given audio file to text.

        Args:
            audio_path: Path to the input audio file (WAV, MP3, etc.).
            language: Optional language code hint (e.g., 'en', 'hi', 'ta').

        Returns:
            STTResult dataclass containing transcription text and metadata metrics.
        """
        pass

    @abstractmethod
    def get_device(self) -> str:
        """
        Returns the active hardware device used for STT inference (cuda, mps, cpu).
        """
        pass
