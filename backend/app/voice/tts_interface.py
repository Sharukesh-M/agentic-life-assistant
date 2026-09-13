"""
Abstract Interface for JARVIX Text-To-Speech (TTS) Engine.
Enables pluggable TTS implementations (OmniVoice, ElevenLabs, local models, etc.)
without changing higher-level agent or API code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class TTSResult:
    audio_path: str
    text: str
    duration_seconds: float
    device: str
    load_time_seconds: float
    generation_time_seconds: float
    real_time_factor: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None

class TTSInterface(ABC):
    """
    Abstract Base Class for JARVIX Text-to-Speech Engine
    """
    
    @abstractmethod
    def synthesize(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        """
        Synthesizes the given text to audio.
        
        Args:
            text: The text string to synthesize.
            output_path: Optional file path to save the generated WAV audio.
            
        Returns:
            TTSResult dataclass containing execution metrics and output details.
        """
        pass

    @abstractmethod
    def get_device(self) -> str:
        """
        Returns the active hardware device used for synthesis (cuda, mps, cpu, etc.).
        """
        pass
