"""
services/learning/gemini_learning_client.py — Centralized Gemini Learning API Client for JARVIS-X

One dedicated Gemini API configuration powering:
- Roadmap & Curriculum Generation
- Lesson & Visual Content Generation
- Task & Daily Schedule Generation
- Quizzes, Assessments & Mock Tests
- Coding Exercises, Hints & Debugging
- Progress Analysis & Recommendation Engine
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class GeminiLearningClient:
    """Centralized, resilient Gemini Learning API Client.
    
    Reads GEMINI_LEARNING_API_KEY and GEMINI_LEARNING_MODEL from environment variables,
    with safe fallbacks and retry logic to prevent crashes.
    """

    def __init__(self):
        self.api_key = (
            os.getenv("GEMINI_LEARNING_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("gemini_api_key")
            or ""
        ).strip()

        self.model_name = (
            os.getenv("GEMINI_LEARNING_MODEL")
            or os.getenv("GEMINI_MODEL")
            or "gemini-2.5-flash"
        ).strip()

        self._client = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                print(f"[GeminiLearningClient] Init warning: {exc}")
                self._client = None

    def is_available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Generates structured JSON data from Gemini with retries and safe fallback."""
        if not self.is_available():
            print("[GeminiLearningClient] API key not configured or client unavailable. Returning fallback.")
            return {"status": "LEARNING_GENERATION_FAILED", "reason": "GEMINI_LEARNING_API_KEY not configured"}

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER PROMPT:\n{prompt}"

        full_prompt += "\n\nCRITICAL: Return ONLY valid, parseable JSON matching the requested schema. Do not include markdown code blocks or prose around the JSON."

        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                )
                duration = round(time.time() - start_time, 2)

                raw_text = response.text if hasattr(response, "text") and response.text else ""
                if not raw_text:
                    continue

                # Clean markdown blocks if present
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                json_match = re.search(r"\{.*\}", clean_text, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group(0))
                    if isinstance(parsed_data, dict):
                        parsed_data["_meta"] = {
                            "model": self.model_name,
                            "latency_sec": duration,
                            "attempt": attempt,
                        }
                        return parsed_data

            except Exception as exc:
                print(f"[GeminiLearningClient] Attempt {attempt}/{max_retries} failed: {exc}")
                time.sleep(1.0 * attempt)

        return {
            "status": "LEARNING_GENERATION_FAILED",
            "reason": "Max retries exceeded or invalid JSON payload",
        }


_learning_client_instance: Optional[GeminiLearningClient] = None


def get_gemini_learning_client() -> GeminiLearningClient:
    global _learning_client_instance
    if _learning_client_instance is None:
        _learning_client_instance = GeminiLearningClient()
    return _learning_client_instance
