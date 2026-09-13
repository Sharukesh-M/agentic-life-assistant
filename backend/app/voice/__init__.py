"""
JARVIX Voice Subsystem - STT and TTS Services
"""
from .tts_interface import TTSInterface, TTSResult
from .omnivoice_service import OmniVoiceTTS

__all__ = ["TTSInterface", "TTSResult", "OmniVoiceTTS"]
