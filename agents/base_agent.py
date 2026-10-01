"""
agents/base_agent.py - JARVIS-X Base Agent Interface

All JARVIS-X agents inherit from BaseAgent. The interface is deliberately
minimal so existing logic (goal_tracker, personal_agent, etc.) can be
wrapped without modification.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Structured response from any JARVIS-X agent.

    Attributes:
        success        -- Whether the agent completed without error
        message        -- Human-readable result (shown to user via LLM)
        data           -- Machine-readable structured data (for chaining agents)
        needs_input    -- True if the agent needs more info from the user
        missing_field  -- The specific field name needed (if needs_input=True)
        next_agent     -- Suggests chaining to another agent
        confidence     -- 0.0-1.0; low = result should be verified
        error          -- Error message if success=False
    """
    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    needs_input: bool = False
    missing_field: Optional[str] = None
    next_agent: Optional[str] = None
    confidence: float = 1.0
    error: str = ""

    def as_str(self) -> str:
        """Return message for use as an LLM tool response."""
        if not self.success:
            return f"Error: {self.error or self.message}"
        return self.message

    def to_dict(self) -> dict:
        return {
            "success":       self.success,
            "message":       self.message,
            "data":          self.data,
            "needs_input":   self.needs_input,
            "missing_field": self.missing_field,
            "next_agent":    self.next_agent,
            "confidence":    self.confidence,
            "error":         self.error,
        }


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract base class for all JARVIS-X agents.

    Subclasses must implement:
        handle(intent, context) -> AgentResult

    Subclasses should set:
        name         -- unique identifier
        description  -- one-line description
        capabilities -- list of capability strings for AgentRegistry routing
        priority     -- routing priority (higher = preferred)
    """

    name: str = "base_agent"
    description: str = "Abstract base agent"
    capabilities: list[str] = []
    priority: int = 0

    def __init__(self) -> None:
        self._log = logging.getLogger(f"jarvis.agent.{self.name}")

    @abstractmethod
    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        """Process the intent with the given context and return a result.

        Args:
            intent   -- The routing intent string (e.g. "create_goal")
            context  -- Dict containing:
                        tool_name, tool_args, session_log,
                        memory, goal_ids, skill_name, ...

        Returns:
            AgentResult with message ready for LLM consumption
        """
        ...

    def __call__(self, intent: str = "", context: dict | None = None) -> str:
        """Make agents callable with the same signature as action handlers."""
        result = self.handle(intent=intent, context=context or {})
        return result.as_str()

    def _log_info(self, msg: str) -> None:
        print(f"[{self.name}] {msg}")
        self._log.info(msg)

    def _log_error(self, msg: str) -> None:
        print(f"[{self.name}] ERROR: {msg}")
        self._log.error(msg)

    def safe_handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        """Wrapper around handle() that never raises.

        Used by AgentRegistry.run() so a crashing agent never takes down
        the audio pipeline.
        """
        try:
            return self.handle(intent=intent, context=context)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return AgentResult(
                success=False,
                error=str(exc),
                message=f"Agent '{self.name}' encountered an error: {exc}",
            )
