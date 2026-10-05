"""
core/agent_bootstrap.py - JARVIS-X Agent Registration

Phase 3: Registers all Phase 2 agents into the process-level AgentRegistry
and wires them to the Orchestrator.

Called once from JarvisLive.__init__(). All agent imports are lazy (inside
the function) so a missing optional dependency never prevents startup.

To add a new agent:
  1. Create it in agents/your_agent.py inheriting BaseAgent
  2. Add one register() call below
  3. Add its tool names to _EXTRA_INTENT_MAP if needed
"""

from __future__ import annotations

import traceback
from typing import Callable


# Extra intent mappings beyond the Orchestrator's built-in _TOOL_INTENT_MAP
_EXTRA_INTENT_MAP: dict[str, list[str]] = {
    "goal_tracker":     ["goal_management", "create_goal", "list_goals",
                         "pause_goal", "resume_goal", "abandon_goal"],
    "personal_agent":   ["goal_management", "next_step"],
    "flashcards":       ["learning", "flashcard"],
    "quiz_mode":        ["learning", "quiz", "record_attempt"],
    "habit_tracker":    ["progress_tracking", "habit"],
    "pomodoro_timer":   ["task_planning", "focus_session"],
    "calendar_plugin":  ["proactive_assistance", "calendar"],
    "reminder":         ["task_planning", "reminder"],
}



def bootstrap(logger_fn: Callable[[str], None] | None = None) -> None:
    """Register all JARVIS-X agents and configure the Orchestrator.

    Safe to call multiple times (register_or_update is idempotent).
    Never raises — a bad agent never prevents startup.
    """
    log = logger_fn or print

    try:
        from core.agent_registry import AgentRecord, get_registry
        from core.orchestrator import get_orchestrator
        registry = get_registry()
        orchestrator = get_orchestrator()
    except Exception as exc:
        log(f"[Bootstrap] FATAL: Could not get registry/orchestrator: {exc}")
        return

    # Register extra intent mappings into the Orchestrator's routing table
    for tool_name, intents in _EXTRA_INTENT_MAP.items():
        try:
            orchestrator.add_intent_mapping(tool_name, intents)
        except Exception as exc:
            log(f"[Bootstrap] Intent mapping error for {tool_name}: {exc}")

    # ── Goal Agent ───────────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.goal_agent",
        class_name="GoalAgent",
        logger_fn=log,
    )

    # ── Planning Agent ───────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.planning_agent",
        class_name="PlanningAgent",
        logger_fn=log,
    )

    # ── Progress Agent ───────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.progress_agent",
        class_name="ProgressAgent",
        logger_fn=log,
    )

    # ── Learning Agent ───────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.learning_agent",
        class_name="LearningAgent",
        logger_fn=log,
    )

    # ── Memory Agent ─────────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.memory_agent",
        class_name="MemoryAgent",
        logger_fn=log,
    )

    # ── Proactive Agent ──────────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.proactive_agent",
        class_name="ProactiveAgent",
        logger_fn=log,
    )

    # ── Communication Agent ──────────────────────────────────────────────────
    _register_agent(
        registry=registry,
        module_path="agents.communication_agent",
        class_name="CommunicationAgent",
        logger_fn=log,
    )

    agent_count = len(registry.names())
    log(f"[Bootstrap] {agent_count} agent(s) registered: {', '.join(registry.names())}")
    log(f"[Bootstrap] Orchestrator routing:\n{orchestrator.describe_routing()}")


def _register_agent(
    registry,
    module_path: str,
    class_name: str,
    logger_fn: Callable[[str], None],
) -> bool:
    """Import and register one agent. Returns True on success.

    Creates an AgentRecord that wraps agent.safe_handle so crashes
    in the agent body never bubble up into the audio pipeline.
    """
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        agent = cls()

        from core.agent_registry import AgentRecord
        record = AgentRecord(
            name=agent.name,
            description=agent.description,
            capabilities=list(agent.capabilities),
            handler=agent.safe_handle,   # safe_handle never raises
            priority=agent.priority,
            enabled=True,
        )
        registry.register_or_update(record)
        logger_fn(f"[Bootstrap] Agent registered: {agent.name} (priority={agent.priority})")
        return True
    except ImportError as exc:
        # Missing optional dependency (e.g. flashcards plugin not installed)
        logger_fn(f"[Bootstrap] Skipped {class_name}: missing dependency — {exc}")
        return False
    except Exception as exc:
        logger_fn(f"[Bootstrap] ERROR registering {class_name}: {exc}")
        traceback.print_exc()
        return False
