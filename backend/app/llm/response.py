"""
LLM Response Data Structure.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class LLMResponse:
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    provider: str = "mock"
    model: str = "mock-model"
    latency_seconds: float = 0.0
    tokens_used: int = 0
    success: bool = True
    error_message: Optional[str] = None
