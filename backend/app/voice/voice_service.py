"""
Unified JARVIX Voice Service.
Connects STT (Speech-to-Text) -> JARVIX Orchestrator -> TTS (Text-to-Speech).
Preserves existing agent, memory, safety, and persistence architecture.
"""

import os
import time
import uuid
import logging
from typing import Optional, Dict, Any

from app.voice.stt_interface import STTInterface, STTResult
from app.voice.stt_service import get_stt_engine
from app.voice.tts_interface import TTSInterface, TTSResult
from app.voice.omnivoice_service import get_tts_engine
from app.voice.audio_processor import AudioNormalizer, AudioInputError

from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext

logger = logging.getLogger("jarvix.voice")

class VoiceService:
    """
    Unified JARVIX End-to-End Voice Subsystem Service.
    Pipeline: Audio Input -> STT -> Text -> JARVIX Orchestrator -> Text Response -> TTS -> Audio Output WAV.
    """

    def __init__(
        self,
        stt_engine: Optional[STTInterface] = None,
        tts_engine: Optional[TTSInterface] = None,
        orchestrator: Optional[JARVIXOrchestrator] = None
    ):
        self.stt_engine = stt_engine or get_stt_engine()
        self.tts_engine = tts_engine or get_tts_engine()
        self.orchestrator = orchestrator or JARVIXOrchestrator()

    def process_audio_chat(
        self,
        audio_path: str,
        user_id: str = "default_user",
        output_filename: Optional[str] = None,
        language: Optional[str] = None,
        db_session: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Processes incoming user voice audio through full JARVIX pipeline.

        Returns structured dictionary containing transcript, response text, audio file path,
        safety confirmation details, and latency breakdown.
        """
        start_time = time.time()

        # Step 1: Validate and normalize incoming audio file
        is_valid, err_msg = AudioNormalizer.validate_audio_file(audio_path)
        if not is_valid:
            logger.error(f"[VoiceService Error] Invalid audio input: {err_msg}")
            return {
                "status": "error",
                "error": err_msg or "Invalid audio input file.",
                "transcript": "",
                "response_text": "",
                "audio_path": "",
                "latency": {"total_seconds": time.time() - start_time}
            }

        try:
            normalized_path = AudioNormalizer.normalize_audio(audio_path)
        except AudioInputError as e:
            return {
                "status": "error",
                "error": str(e),
                "transcript": "",
                "response_text": "",
                "audio_path": "",
                "latency": {"total_seconds": time.time() - start_time}
            }

        # Step 2: Speech-to-Text (STT) Transcription
        stt_start = time.time()
        stt_res: STTResult = self.stt_engine.transcribe(normalized_path, language=language)
        stt_latency = time.time() - stt_start

        if not stt_res.success or not stt_res.text.strip():
            logger.error(f"[VoiceService Error] STT failed: {stt_res.error_message}")
            return {
                "status": "error",
                "error": stt_res.error_message or "Speech-to-text transcription produced empty result.",
                "transcript": stt_res.text,
                "response_text": "",
                "audio_path": "",
                "latency": {
                    "stt_seconds": stt_latency,
                    "total_seconds": time.time() - start_time
                }
            }

        user_transcript = stt_res.text.strip()
        detected_language = stt_res.language or language or "en"

        # Step 3: JARVIX Agent Orchestration Execution
        orch_start = time.time()
        if db_session:
            context = AgentContext.load_from_db(user_id=user_id, query=user_transcript, session=db_session)
        else:
            context = AgentContext(user_id=user_id)

        orch_res = self.orchestrator.execute_pipeline(
            user_request=user_transcript,
            context=context,
            db_session=db_session
        )
        orch_latency = time.time() - orch_start

        orch_status = orch_res.get("status", "completed")
        intent = orch_res.get("intent", "general_conversation")
        confirmation_prompt = orch_res.get("confirmation_prompt")

        # Step 4: Extract Response Text for TTS Synthesis
        if orch_status == "requires_confirmation":
            response_text = confirmation_prompt or "This action is high-impact and requires your explicit confirmation before proceeding."
        elif orch_status == "completed":
            result_data = orch_res.get("result", {})
            if isinstance(result_data, dict):
                if "response" in result_data:
                    response_text = str(result_data["response"])
                elif "type" in result_data and result_data["type"] == "plan":
                    plan_info = result_data.get("data", {})
                    goal_name = plan_info.goal if hasattr(plan_info, "goal") else plan_info.get("goal", "Goal")
                    ms_count = len(plan_info.milestones if hasattr(plan_info, "milestones") else plan_info.get("milestones", []))
                    response_text = f"I have created a plan for your goal: {goal_name} with {ms_count} milestones."
                elif "type" in result_data and result_data["type"] == "clarification_needed":
                    response_text = result_data.get("data", {}).get("clarifying_question", "Could you please clarify your request?")
                else:
                    response_text = str(result_data)
            else:
                response_text = str(result_data)
        else:
            err_details = orch_res.get("result", {}).get("error", "Failed to process request.") if isinstance(orch_res.get("result"), dict) else "Failed to process request."
            response_text = f"I encountered an error: {err_details}"

        # Step 5: Text-to-Speech (TTS) Synthesis
        tts_start = time.time()
        if not output_filename:
            output_filename = f"jarvix_voice_{uuid.uuid4().hex[:8]}.wav"
        
        output_audio_path = os.path.join("outputs", "audio", output_filename)
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)

        tts_res: TTSResult = self.tts_engine.synthesize(response_text, output_path=output_audio_path)
        tts_latency = time.time() - tts_start

        if not tts_res.success:
            logger.error(f"[VoiceService Error] TTS synthesis failed: {tts_res.error_message}")
            return {
                "status": "error",
                "error": tts_res.error_message or "Text-to-speech audio synthesis failed.",
                "transcript": user_transcript,
                "detected_language": detected_language,
                "response_text": response_text,
                "audio_path": "",
                "orchestrator_status": orch_status,
                "intent": intent,
                "confirmation_prompt": confirmation_prompt,
                "latency": {
                    "stt_seconds": stt_latency,
                    "llm_seconds": orch_latency,
                    "tts_seconds": tts_latency,
                    "total_seconds": time.time() - start_time
                }
            }

        total_latency = time.time() - start_time

        return {
            "status": "success",
            "transcript": user_transcript,
            "detected_language": detected_language,
            "response_text": response_text,
            "audio_path": tts_res.audio_path,
            "orchestrator_status": orch_status,
            "intent": intent,
            "required_capabilities": orch_res.get("required_capabilities", []),
            "required_tools": orch_res.get("required_tools", []),
            "confirmation_prompt": confirmation_prompt,
            "latency": {
                "stt_seconds": stt_latency,
                "llm_seconds": orch_latency,
                "tts_seconds": tts_latency,
                "total_seconds": total_latency
            }
        }
