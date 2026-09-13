"""
FastAPI Router for JARVIX Voice API endpoints.
Endpoints:
- POST /api/voice/transcribe
- POST /api/voice/tts
- POST /api/voice/chat
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = object

try:
    from fastapi import APIRouter, HTTPException, Depends
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = None
    HTTPException = Exception
    Depends = lambda x=None: None

from app.voice.omnivoice_service import get_tts_engine
from app.voice.stt_service import get_stt_engine
from app.voice.voice_service import VoiceService
from app.db.models.base import HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

if HAS_PYDANTIC:
    class TranscribeRequest(BaseModel):
        audio_path: str
        language: Optional[str] = None

    class TranscribeResponse(BaseModel):
        status: str
        transcript: str
        language: str
        confidence: float
        duration_seconds: float
        device: str
        inference_time_seconds: float

    class TTSRequest(BaseModel):
        text: str
        output_filename: Optional[str] = "jarvix_response.wav"

    class TTSResponse(BaseModel):
        status: str
        audio_path: str
        device: str
        load_time_seconds: float
        generation_time_seconds: float
        real_time_factor: float
        error: Optional[str] = None

    class VoiceChatRequest(BaseModel):
        audio_path: str
        user_id: Optional[str] = "default_user"
        language: Optional[str] = None
        output_filename: Optional[str] = None

    class LatencyBreakdown(BaseModel):
        stt_seconds: Optional[float] = 0.0
        llm_seconds: Optional[float] = 0.0
        tts_seconds: Optional[float] = 0.0
        total_seconds: float

    class VoiceChatResponse(BaseModel):
        status: str
        transcript: str
        detected_language: Optional[str] = "en"
        response_text: str
        audio: str
        orchestrator_status: Optional[str] = "completed"
        intent: Optional[str] = "general_conversation"
        required_capabilities: Optional[List[str]] = []
        confirmation_prompt: Optional[str] = None
        latency: LatencyBreakdown
        error: Optional[str] = None
else:
    @dataclass
    class TranscribeRequest:
        audio_path: str
        language: Optional[str] = None

    @dataclass
    class TranscribeResponse:
        status: str
        transcript: str
        language: str
        confidence: float
        duration_seconds: float
        device: str
        inference_time_seconds: float

    @dataclass
    class TTSRequest:
        text: str
        output_filename: Optional[str] = "jarvix_response.wav"

    @dataclass
    class TTSResponse:
        status: str
        audio_path: str
        device: str
        load_time_seconds: float
        generation_time_seconds: float
        real_time_factor: float
        error: Optional[str] = None

    @dataclass
    class VoiceChatRequest:
        audio_path: str
        user_id: Optional[str] = "default_user"
        language: Optional[str] = None
        output_filename: Optional[str] = None

    @dataclass
    class LatencyBreakdown:
        total_seconds: float
        stt_seconds: Optional[float] = 0.0
        llm_seconds: Optional[float] = 0.0
        tts_seconds: Optional[float] = 0.0

    @dataclass
    class VoiceChatResponse:
        status: str
        transcript: str
        detected_language: Optional[str]
        response_text: str
        audio: str
        orchestrator_status: Optional[str]
        intent: Optional[str]
        required_capabilities: Optional[List[str]]
        confirmation_prompt: Optional[str]
        latency: Any
        error: Optional[str] = None

stt_service = get_stt_engine()
tts_service = get_tts_engine()
voice_service = VoiceService(stt_engine=stt_service, tts_engine=tts_service)

async def transcribe_speech(request: Any):
    """
    Transcribe speech audio file to text using STT engine.
    """
    audio_path = getattr(request, "audio_path", "")
    language = getattr(request, "language", None)
    result = stt_service.transcribe(audio_path, language=language)
    if not result.success:
        if HAS_FASTAPI:
            raise HTTPException(status_code=400, detail=result.error_message or "STT transcription failed.")
        else:
            raise ValueError(result.error_message or "STT transcription failed.")

    return TranscribeResponse(
        status="success",
        transcript=result.text,
        language=result.language or "en",
        confidence=result.confidence,
        duration_seconds=result.duration_seconds,
        device=result.device,
        inference_time_seconds=result.inference_time_seconds
    )

async def synthesize_speech(request: Any):
    """
    Synthesize JARVIX text response into speech audio using TTS engine.
    """
    text = getattr(request, "text", "")
    output_filename = getattr(request, "output_filename", "jarvix_response.wav")

    if not text or not text.strip():
        if HAS_FASTAPI:
            raise HTTPException(status_code=400, detail="Text field cannot be empty.")
        else:
            raise ValueError("Text field cannot be empty.")

    output_path = f"outputs/audio/{output_filename}"
    result = tts_service.synthesize(text, output_path=output_path)

    if not result.success:
        if HAS_FASTAPI:
            raise HTTPException(status_code=500, detail=result.error_message or "TTS synthesis failed.")
        else:
            raise RuntimeError(result.error_message or "TTS synthesis failed.")

    return TTSResponse(
        status="success",
        audio_path=result.audio_path,
        device=result.device,
        load_time_seconds=result.load_time_seconds,
        generation_time_seconds=result.generation_time_seconds,
        real_time_factor=result.real_time_factor
    )

async def voice_chat_endpoint(request: Any, db: Any = None):
    """
    JARVIX End-to-End Voice Chat API Endpoint.
    Audio -> STT -> JARVIX Orchestrator -> Response -> TTS -> Audio File.
    """
    audio_path = getattr(request, "audio_path", "")
    user_id = getattr(request, "user_id", "default_user") or "default_user"
    output_filename = getattr(request, "output_filename", None)
    language = getattr(request, "language", None)

    result = voice_service.process_audio_chat(
        audio_path=audio_path,
        user_id=user_id,
        output_filename=output_filename,
        language=language,
        db_session=db
    )

    if result.get("status") == "error":
        if HAS_FASTAPI:
            raise HTTPException(status_code=400, detail=result.get("error", "Voice pipeline processing failed."))
        else:
            raise ValueError(result.get("error", "Voice pipeline processing failed."))

    lat = result.get("latency", {})
    return VoiceChatResponse(
        status=result.get("status", "success"),
        transcript=result.get("transcript", ""),
        detected_language=result.get("detected_language", "en"),
        response_text=result.get("response_text", ""),
        audio=result.get("audio_path", ""),
        orchestrator_status=result.get("orchestrator_status", "completed"),
        intent=result.get("intent", "general_conversation"),
        required_capabilities=result.get("required_capabilities", []),
        confirmation_prompt=result.get("confirmation_prompt"),
        latency=LatencyBreakdown(
            stt_seconds=lat.get("stt_seconds", 0.0),
            llm_seconds=lat.get("llm_seconds", 0.0),
            tts_seconds=lat.get("tts_seconds", 0.0),
            total_seconds=lat.get("total_seconds", 0.0)
        )
    )

if HAS_FASTAPI:
    router = APIRouter(prefix="/api/voice", tags=["voice"])
    router.add_api_route("/transcribe", transcribe_speech, methods=["POST"], response_model=TranscribeResponse)
    router.add_api_route("/tts", synthesize_speech, methods=["POST"], response_model=TTSResponse)
    router.add_api_route("/chat", voice_chat_endpoint, methods=["POST"], response_model=VoiceChatResponse)
else:
    router = None
