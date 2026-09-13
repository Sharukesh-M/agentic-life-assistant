"""
LLM Configuration Module.
Loads environment variables for provider, model name, API key, and base URL.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: float = 30.0
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> 'LLMConfig':
        provider = os.getenv("LLM_PROVIDER", "mock").lower()
        model = os.getenv("LLM_MODEL", "jarvix-default-model")
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("LLM_BASE_URL")
        timeout = float(os.getenv("LLM_TIMEOUT", "30.0"))
        temp = float(os.getenv("LLM_TEMPERATURE", "0.0"))

        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            temperature=temp
        )
