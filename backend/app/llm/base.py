"""
Base Abstract LLM Provider Interface.
Keeps JARVIX independent from specific AI model vendors.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type
from app.llm.response import LLMResponse

class BaseLLMProvider(ABC):

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format_json: bool = False,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """
        Generates completion from target LLM model.
        """
        pass
