"""
core/agent_registry.py - JARVIS-X Agent Registry

Phase 2 addition: A clean registry that stores and routes to specialized
agents. New agents are registered here; the Orchestrator queries this
registry to find the right agent for a given intent.

No existing code is modified. JarvisLive's _execute_tool continues to work
unchanged until Phase 3 explicitly wires the Orchestrator in.
"""

from __future__ import annotations

import inspect
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("jarvis.agent_registry")


# ---------------------------------------------------------------------------
# Agent Record
# ---------------------------------------------------------------------------

@dataclass
class AgentRecord:
    """Metadata and callable for one registered agent.

    Attributes:
        name        -- Unique identifier, e.g. "goal_agent"
        description -- Human-readable description of what the agent does
        capabilities-- List of capability strings, e.g. ["create_goal", "list_goals"]
        handler     -- Async or sync callable: handler(intent, context) -> str | dict
        priority    -- Higher priority agents are preferred when multiple match
        enabled     -- Can be toggled at runtime without removing from registry
    """
    name: str
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    priority: int = 0
    enabled: bool = True
    _meta: dict[str, Any] = field(default_factory=dict, repr=False)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Stores and routes to JARVIS-X agents.

    Usage:
        registry = AgentRegistry()
        registry.register(AgentRecord(name="goal_agent", ...))
        agent = registry.get("goal_agent")
        result = registry.run("goal_agent", intent="create_goal", context={...})
    """

    def __init__(self, logger_fn: Callable[[str], None] | None = None) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._log = logger_fn or (lambda msg: logger.info(msg))

    # ── Registration ────────────────────────────────────────────────────────

    def register(self, record: AgentRecord) -> None:
        """Register an agent. Raises ValueError on duplicate name."""
        if record.name in self._agents:
            raise ValueError(f"Agent '{record.name}' is already registered.")
        if not record.name or not record.name.replace("_", "").isalnum():
            raise ValueError(f"Invalid agent name: '{record.name}'")
        self._agents[record.name] = record
        self._log(f"[AgentRegistry] Registered agent: {record.name}")

    def register_or_update(self, record: AgentRecord) -> None:
        """Register or silently replace an existing agent (for hot-reload)."""
        self._agents[record.name] = record
        self._log(f"[AgentRegistry] Registered/updated agent: {record.name}")

    def unregister(self, name: str) -> bool:
        """Remove an agent. Returns True if it existed."""
        if name in self._agents:
            del self._agents[name]
            self._log(f"[AgentRegistry] Unregistered agent: {name}")
            return True
        return False

    def enable(self, name: str) -> None:
        if name in self._agents:
            self._agents[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._agents:
            self._agents[name].enabled = False

    # ── Lookup ──────────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[AgentRecord]:
        """Return the agent record or None."""
        return self._agents.get(name)

    def has(self, name: str) -> bool:
        return name in self._agents

    def list(self, enabled_only: bool = False) -> list[AgentRecord]:
        """Return all registered agents, optionally filtered to enabled ones."""
        records = list(self._agents.values())
        if enabled_only:
            records = [r for r in records if r.enabled]
        return sorted(records, key=lambda r: -r.priority)

    def names(self) -> list[str]:
        return list(self._agents.keys())

    # ── Routing ─────────────────────────────────────────────────────────────

    def route(self, intent: str, context: dict | None = None) -> Optional[AgentRecord]:
        """Find the best enabled agent for the given intent string.

        Matching strategy (in priority order):
        1. Exact name match (intent == agent.name)
        2. Capability match (intent in agent.capabilities)
        3. Substring match in description (intent as keyword)

        Among multiple matches, the highest-priority agent wins.
        Returns None if no suitable agent is found.
        """
        intent_lower = intent.lower().strip()
        candidates: list[AgentRecord] = []

        for record in self._agents.values():
            if not record.enabled:
                continue

            # Exact name match
            if record.name == intent_lower:
                candidates.append(record)
                continue

            # Capability match
            if any(cap.lower() == intent_lower for cap in record.capabilities):
                candidates.append(record)
                continue

            # Keyword in capabilities list
            if any(intent_lower in cap.lower() for cap in record.capabilities):
                candidates.append(record)
                continue

            # Keyword in description
            if intent_lower in record.description.lower():
                candidates.append(record)

        if not candidates:
            return None

        return max(candidates, key=lambda r: r.priority)

    def route_all(self, intent: str) -> list[AgentRecord]:
        """Return all agents that match the intent (sorted by priority desc)."""
        matched = []
        intent_lower = intent.lower().strip()
        for record in self._agents.values():
            if not record.enabled:
                continue
            if (record.name == intent_lower
                    or any(intent_lower in cap.lower() for cap in record.capabilities)
                    or intent_lower in record.description.lower()):
                matched.append(record)
        return sorted(matched, key=lambda r: -r.priority)

    # ── Execution ────────────────────────────────────────────────────────────

    def run(
        self,
        name: str,
        intent: str = "",
        context: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Invoke an agent by name synchronously.

        The handler receives whichever of (intent, context, **kwargs) its
        signature actually declares, so existing agent signatures work unchanged.

        Returns a string result. On error, returns an error string (never raises).
        """
        record = self._agents.get(name)
        if record is None:
            return f"Agent '{name}' is not registered."
        if not record.enabled:
            return f"Agent '{name}' is currently disabled."
        if record.handler is None:
            return f"Agent '{name}' has no handler."

        try:
            return _call_handler(record.handler, intent=intent, context=context or {}, **kwargs)
        except Exception as exc:
            self._log(f"[AgentRegistry] Agent '{name}' crashed: {exc}")
            traceback.print_exc()
            return f"Agent '{name}' failed: {exc}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_handler(
    fn: Callable,
    intent: str,
    context: dict,
    **extra: Any,
) -> str:
    """Call a handler, passing only the kwargs it actually declares."""
    sig = inspect.signature(fn)
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    kwargs: dict[str, Any] = {}
    available = {"intent": intent, "context": context, **extra}
    for key, val in available.items():
        if has_var_kw or key in sig.parameters:
            kwargs[key] = val
    result = fn(**kwargs)
    return str(result) if result is not None else "Done."


# ---------------------------------------------------------------------------
# Process-level default registry (lazy singleton)
# ---------------------------------------------------------------------------

_default_registry: Optional[AgentRegistry] = None
_registry_lock = __import__("threading").Lock()


def get_registry() -> AgentRegistry:
    """Return the process-level AgentRegistry singleton."""
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                _default_registry = AgentRegistry(
                    logger_fn=lambda m: print(m)
                )
    return _default_registry


def reset_registry() -> None:
    """Reset the singleton (for tests only)."""
    global _default_registry
    with _registry_lock:
        _default_registry = None
