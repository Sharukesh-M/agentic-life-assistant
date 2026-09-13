"""
LLM Provider Implementations:
1. MockLLMProvider: Deterministic test & fallback provider
2. OpenAILikeLLMProvider: Standard HTTP provider for OpenAI, Gemini, Anthropic, or OpenAI-compatible endpoints
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from app.llm.base import BaseLLMProvider
from app.llm.response import LLMResponse
from app.llm.config import LLMConfig


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic Mock LLM Provider for unit testing and offline execution.
    Inspects input prompt to produce valid JSON responses matching JARVIX schemas.
    """

    def __init__(self, model_name: str = "jarvix-mock-engine"):
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format_json: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        start_time = time.time()
        combined_text = (system_prompt or "") + "\n" + prompt

        # 1. Orchestration Routing Case
        if "JARVIX Orchestrator" in combined_text or "AVAILABLE CAPABILITIES" in combined_text:
            req_text = prompt
            if "CURRENT_USER_REQUEST:" in prompt:
                req_text = prompt.split("CURRENT_USER_REQUEST:")[-1]
            req_lower = req_text.lower()

            if "calendar" in req_lower or "schedule" in req_lower:
                payload = {
                    "intent": "calendar_schedule",
                    "required_capabilities": ["Calendar", "Tool Use"],
                    "required_tools": ["google_calendar"],
                    "authorization_checked": True,
                    "authorization_status": "authorized",
                    "requires_confirmation": True,
                    "confirmation_prompt": "This will add an event to your primary Google Calendar. Proceed?"
                }
            elif "plan" in req_lower or "learn" in req_lower or "exam" in req_lower:
                payload = {
                    "intent": "goal_planning",
                    "required_capabilities": ["Goal Management", "Planning"],
                    "required_tools": [],
                    "authorization_checked": True,
                    "authorization_status": "authorized",
                    "requires_confirmation": False,
                    "confirmation_prompt": None
                }
            else:
                payload = {
                    "intent": "general_conversation",
                    "required_capabilities": ["General Conversation"],
                    "required_tools": [],
                    "authorization_checked": True,
                    "authorization_status": "not_applicable",
                    "requires_confirmation": False,
                    "confirmation_prompt": None
                }
            text_resp = json.dumps(payload, indent=2)
            parsed = payload

        # 2. Planning Agent Case
        elif "Planning Agent" in combined_text or "GOAL:" in prompt:
            if "clarify" in prompt.lower() and "missing" in prompt.lower():
                payload = {
                    "status": "clarification_needed",
                    "questions": [
                        "What is your target completion deadline?",
                        "How many hours per day can you dedicate to this goal?"
                    ]
                }
            else:
                payload = {
                    "status": "plan",
                    "goal": "Learn Generative AI in 30 Days",
                    "assumptions": ["Basic Python proficiency", "Access to GPU/Cloud notebook environment"],
                    "milestones": [
                        {
                            "title": "Phase 1: Foundations of Transformers & LLMs",
                            "description": "Understand attention mechanisms and transformer architecture",
                            "tasks": [
                                {
                                    "title": "Study Attention Is All You Need paper",
                                    "description": "Read and annotate self-attention mathematical formulation",
                                    "priority": "HIGH",
                                    "estimated_minutes": 120,
                                    "depends_on": []
                                },
                                {
                                    "title": "Implement Toy Self-Attention in PyTorch",
                                    "description": "Code matrix query-key-value scaling from scratch",
                                    "priority": "HIGH",
                                    "estimated_minutes": 180,
                                    "depends_on": ["Study Attention Is All You Need paper"]
                                }
                            ]
                        },
                        {
                            "title": "Phase 2: Fine-Tuning & RAG Integration",
                            "description": "Build RAG pipeline and LoRA fine-tuning script",
                            "tasks": [
                                {
                                    "title": "Setup Vector Database with ChromaDB",
                                    "description": "Index PDF documents for semantic search",
                                    "priority": "MEDIUM",
                                    "estimated_minutes": 150,
                                    "depends_on": []
                                }
                            ]
                        }
                    ]
                }
            text_resp = json.dumps(payload, indent=2)
            parsed = payload

        # 3. Goal Management / Event Correlation Case
        elif "Goal Management" in combined_text or "INCOMING_EXTERNAL_OBSERVATION:" in prompt:
            p_lower = prompt.lower()
            if "sports" in p_lower or "tennis" in p_lower:
                payload = {
                    "matches": [],
                    "no_relevant_goals": True
                }
            elif "multi" in p_lower or "career" in p_lower or "job" in p_lower:
                payload = {
                    "matches": [
                        {
                            "goal_id": "g_genai",
                            "relevance_score": 0.88,
                            "goal_priority": "HIGH",
                            "reason": "Topical match for Generative AI learning goal.",
                            "suggested_action": "recommend"
                        },
                        {
                            "goal_id": "g_career",
                            "relevance_score": 0.75,
                            "goal_priority": "MEDIUM",
                            "reason": "Opportunity aligns with engineering career advancement goal.",
                            "suggested_action": "recommend"
                        }
                    ],
                    "no_relevant_goals": False
                }
            else:
                payload = {
                    "matches": [
                        {
                            "goal_id": "g_genai",
                            "relevance_score": 0.88,
                            "goal_priority": "HIGH",
                            "reason": "Topical match for Generative AI learning goal.",
                            "suggested_action": "recommend"
                        }
                    ],
                    "no_relevant_goals": False
                }
            text_resp = json.dumps(payload, indent=2)
            parsed = payload

        # 4. Memory Agent Case
        elif "Memory Agent" in combined_text:
            payload = {
                "operation": "store",
                "classification": "LONG_TERM_PREFERENCE",
                "content": "Prefers code-first examples and structured 30-day learning schedules.",
                "reason": "User explicitly stated preference for worked examples and structured study."
            }
            text_resp = json.dumps(payload, indent=2)
            parsed = payload

        # 4. Fallback / General Conversation
        else:
            text_resp = "Hello! I am JARVIX, your goal-aware proactive AI life assistant. I can help decompose your personal or professional goals into actionable task plans, track progress, manage memory, and assist with your daily schedule. What would you like to achieve today?"
            parsed = None

        latency = time.time() - start_time
        return LLMResponse(
            text=text_resp,
            parsed_json=parsed,
            provider="mock",
            model=self.model_name,
            latency_seconds=latency,
            tokens_used=len(text_resp.split()),
            success=True
        )


class OpenAILikeLLMProvider(BaseLLMProvider):
    """
    HTTP Client LLM Provider supporting OpenAI-compatible REST endpoints.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or "https://api.openai.com/v1/chat/completions"
        self.api_key = config.api_key or ""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format_json: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                text="",
                provider=self.config.provider,
                model=self.config.model,
                success=False,
                error_message="Missing API key. Configure LLM_API_KEY or OPENAI_API_KEY environment variable."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                latency = time.time() - start_time

                content = resp_data["choices"][0]["message"]["content"]
                tokens = resp_data.get("usage", {}).get("total_tokens", 0)

                parsed_json = None
                if response_format_json:
                    try:
                        parsed_json = json.loads(content)
                    except json.JSONDecodeError:
                        parsed_json = None

                return LLMResponse(
                    text=content,
                    parsed_json=parsed_json,
                    provider=self.config.provider,
                    model=self.config.model,
                    latency_seconds=latency,
                    tokens_used=tokens,
                    success=True
                )
        except Exception as e:
            latency = time.time() - start_time
            return LLMResponse(
                text="",
                provider=self.config.provider,
                model=self.config.model,
                latency_seconds=latency,
                success=False,
                error_message=f"LLM Provider execution error: {str(e)}"
            )


def get_llm_provider(config: Optional[LLMConfig] = None) -> BaseLLMProvider:
    """
    Factory function returning active LLM provider instance.
    """
    if config is None:
        config = LLMConfig.from_env()

    if config.provider in ("openai", "openai-compatible", "vllm", "ollama"):
        if config.api_key or config.base_url:
            return OpenAILikeLLMProvider(config)
        else:
            print("[JARVIX LLM] No API key found for provider. Falling back to MockLLMProvider.")
            return MockLLMProvider(model_name="jarvix-mock-engine")
    else:
        return MockLLMProvider(model_name=config.model)
