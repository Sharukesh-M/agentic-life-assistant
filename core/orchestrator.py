"""
core/orchestrator.py - JARVIS-X Orchestrator

Phase 2 addition: Sits between the LLM tool-call dispatch and the actual
tool/agent execution. The Orchestrator's job is to:

  1. Determine user intent from the tool call + context
  2. Select the appropriate agent (if any) from the AgentRegistry
  3. Load the relevant skill context (if any) from the SkillRegistry
  4. Dispatch to agent, or fall through to the existing tool/plugin dispatch

In Phase 2, the routing table is mostly empty (falls through to existing
_execute_tool). In Phase 3, agents are registered and routing activates.

No existing code is modified. JarvisLive._execute_tool continues to handle
all tool calls; the Orchestrator is wired in as an optional pre-step.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("jarvis.orchestrator")


# ---------------------------------------------------------------------------
# Orchestration Request / Decision
# ---------------------------------------------------------------------------

@dataclass
class OrchestratorRequest:
    """Everything the Orchestrator knows when it receives a tool call."""
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    session_log: list[str] = field(default_factory=list)
    memory_snapshot: dict[str, Any] = field(default_factory=dict)
    active_goal_ids: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class OrchestratorDecision:
    """What the Orchestrator decided to do with the request.

    Attributes:
        handled      -- True if the Orchestrator fully handled it
                        (result is ready, _execute_tool should not run)
        agent_name   -- Which agent was invoked (if any)
        skill_name   -- Which skill context was loaded (if any)
        result       -- The string result (set when handled=True)
        log_message  -- One-line structured log entry
        confidence   -- 0.0-1.0; low confidence means fall-through to tools
    """
    handled: bool = False
    agent_name: Optional[str] = None
    skill_name: Optional[str] = None
    result: Optional[str] = None
    log_message: str = ""
    confidence: float = 1.0
    needs_user_input: bool = False
    follow_up: Optional[str] = None


# ---------------------------------------------------------------------------
# Intent keywords -> agent capability mapping
# ---------------------------------------------------------------------------

# Maps tool_name -> list of capability/intent hints for the AgentRegistry router.
# This table grows as agents are registered in Phase 3.
_TOOL_INTENT_MAP: dict[str, list[str]] = {
    "workspace_action": ["task_service", "workspace_management", "create_task", "create_tasks", "get_today_tasks", "get_task", "update_task", "complete_task", "postpone_task", "reschedule_task", "delete_task", "start_task", "open_workspace", "open_today_tasks", "open_learning_workspace", "open_goal_workspace", "refresh_workspace"],
    "task_service":     ["task_service", "create_task", "create_tasks", "get_today_tasks", "update_task", "complete_task", "delete_task"],
    "workspace_manager":["workspace_management", "open_workspace", "open_today_workspace", "open_learning_workspace", "open_goal_workspace", "open_progress_workspace"],
    "goal_tracker":    ["goal_management", "create_goal", "list_goals", "update_goal"],
    "personal_agent":  ["goal_management", "next_step"],
    "reminder":        ["reminder_management", "create_reminder"],
    "habit_tracker":   ["habit_tracking"],
    "flashcards":      ["learning", "flashcard"],
    "quiz_mode":       ["learning", "quiz"],
    "pomodoro_timer":  ["task_planning", "focus_session"],
    "calendar_plugin": ["proactive_assistance", "calendar"],
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Routes tool calls to agents where appropriate; falls through otherwise.

    The Orchestrator is designed to be called BEFORE _execute_tool in
    JarvisLive. If it returns a Decision with handled=True, _execute_tool
    should not be called for that turn. If handled=False, fall through
    normally.

    In Phase 2, the Orchestrator always returns handled=False (transparent
    fall-through). Routing activates in Phase 3 as agents are registered.
    """

    def __init__(
        self,
        agent_registry=None,   # core.agent_registry.AgentRegistry
        skill_registry=None,   # core.skill_loader.SkillRegistry
        logger_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._agents = agent_registry
        self._skills = skill_registry
        self._log = logger_fn or (lambda m: logger.info(m))
        self._total_requests: int = 0
        self._agent_hits: int = 0

    def route(self, request: OrchestratorRequest) -> OrchestratorDecision:
        """Main entry point. Returns a Decision synchronously.

        Falls through (handled=False) when:
        - No agent is registered for this tool
        - Agent routing confidence is too low
        - Any error occurs (fail-safe: never break the existing flow)
        """
        self._total_requests += 1
        try:
            return self._route_internal(request)
        except Exception as exc:
            self._log(f"[Orchestrator] ERROR in route(): {exc} -- falling through")
            return OrchestratorDecision(
                handled=False,
                log_message=f"Orchestrator error (safe fall-through): {exc}",
                confidence=0.0,
            )

    def _route_internal(self, request: OrchestratorRequest) -> OrchestratorDecision:
        tool = request.tool_name

        # ── Step 1: Determine intents for this tool call ────────────────────
        intents = _TOOL_INTENT_MAP.get(tool, [tool])

        # ── Step 2: Try AgentRegistry routing ───────────────────────────────
        if self._agents is not None:
            best_agent = None
            for intent in intents:
                candidate = self._agents.route(intent)
                if candidate is not None:
                    best_agent = candidate
                    break

            if best_agent is not None and best_agent.handler is not None:
                # ── Step 3: Load skill context if available ─────────────────
                skill_name = None
                if self._skills is not None:
                    skill = self._skills.find_by_trigger(tool)
                    if skill:
                        skill_name = skill.name

                # ── Step 4: Run the agent ───────────────────────────────────
                self._agent_hits += 1
                self._log(
                    f"[Orchestrator] {tool} -> agent={best_agent.name}"
                    f"{f' skill={skill_name}' if skill_name else ''}"
                )
                result = self._agents.run(
                    best_agent.name,
                    intent=intents[0] if intents else tool,
                    context={
                        "tool_name":    tool,
                        "tool_args":    request.tool_args,
                        "session_log":  request.session_log,
                        "memory":       request.memory_snapshot,
                        "goal_ids":     request.active_goal_ids,
                        "skill_name":   skill_name,
                    },
                )
                return OrchestratorDecision(
                    handled=True,
                    agent_name=best_agent.name,
                    skill_name=skill_name,
                    result=result,
                    log_message=(
                        f"Routed {tool} -> {best_agent.name} "
                        f"(skill={skill_name or 'none'})"
                    ),
                    confidence=1.0,
                )

        # ── Fall-through: let _execute_tool handle as normal ────────────────
        return OrchestratorDecision(
            handled=False,
            log_message=f"Fall-through: no agent registered for '{tool}'",
            confidence=0.0,
        )

    # ── Observability ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "agent_hits":     self._agent_hits,
            "fall_throughs":  self._total_requests - self._agent_hits,
        }

    def describe_routing(self) -> str:
        """Human-readable routing table (for debugging)."""
        lines = ["[Orchestrator] Routing table:"]
        for tool, intents in sorted(_TOOL_INTENT_MAP.items()):
            lines.append(f"  {tool:25s} -> {', '.join(intents)}")
        return "\n".join(lines)

    def add_intent_mapping(self, tool_name: str, intents: list[str]) -> None:
        """Dynamically add intent mappings (for plugins or new agents)."""
        existing = _TOOL_INTENT_MAP.get(tool_name, [])
        _TOOL_INTENT_MAP[tool_name] = list(dict.fromkeys(existing + intents))


# ---------------------------------------------------------------------------
# Process-level default orchestrator (lazy singleton)
# ---------------------------------------------------------------------------

_default_orchestrator: Optional[Orchestrator] = None
_orch_lock = __import__("threading").Lock()


def get_orchestrator() -> Orchestrator:
    """Return the process-level Orchestrator singleton."""
    global _default_orchestrator
    if _default_orchestrator is None:
        with _orch_lock:
            if _default_orchestrator is None:
                # Import lazily to avoid circular imports at module load time
                try:
                    from core.agent_registry import get_registry
                    from core.skill_loader import get_skill_registry
                    _default_orchestrator = Orchestrator(
                        agent_registry=get_registry(),
                        skill_registry=get_skill_registry(),
                        logger_fn=lambda m: print(m),
                    )
                except ImportError:
                    # skill_loader may not exist yet in Phase 2 — degrade gracefully
                    try:
                        from core.agent_registry import get_registry
                        _default_orchestrator = Orchestrator(
                            agent_registry=get_registry(),
                            logger_fn=lambda m: print(m),
                        )
                    except ImportError:
                        _default_orchestrator = Orchestrator(
                            logger_fn=lambda m: print(m),
                        )
    return _default_orchestrator


def reset_orchestrator() -> None:
    """Reset the singleton (for tests only)."""
    global _default_orchestrator
    with _orch_lock:
        _default_orchestrator = None
