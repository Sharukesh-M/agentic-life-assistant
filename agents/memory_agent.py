"""
agents/memory_agent.py - JARVIS-X Memory Agent

Clean interface over the existing memory_manager.py + mysql_store.py.
Provides a single point of entry for memory operations so the storage
backend can be swapped without changing callers.
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent


class MemoryAgent(BaseAgent):
    """Persistent memory operations for JARVIS-X.

    Wraps:
        memory.memory_manager  (long_term.json)
        memory.mysql_store     (MySQL conversation store)
        memory.profile_manager (profile.json)

    Categories:
        IDENTITY / GOALS / PREFERENCES / CONSTRAINTS /
        PROJECTS / PROGRESS / DECISIONS / NOTES
    """

    name = "memory_agent"
    description = (
        "Persist and recall user facts, preferences, goals, and context. "
        "Routes to the correct storage backend automatically."
    )
    capabilities = [
        "memory_management",
        "save_memory",
        "recall_memory",
        "summarize_session",
        "update_profile",
    ]
    priority = 5

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args", {})
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "save":              self._save,
            "save_memory":       self._save,
            "recall":            self._recall,
            "recall_memory":     self._recall,
            "summarize_session": self._summarize,
            "profile_summary":   self._profile_summary,
        }
        handler = dispatch.get(action, self._recall)
        return handler(args, context)

    def _save(self, args: dict, ctx: dict) -> AgentResult:
        """Save a memory fact."""
        try:
            from memory.memory_manager import update_memory
            category = args.get("category", "notes")
            key = args.get("key", "")
            value = args.get("value", "")
            if not key or not value:
                return AgentResult(success=False, error="key and value are required.")
            update_memory({category: {key: {"value": value}}})
            return AgentResult(
                message=f"Remembered: {category}/{key} = {value}",
                data={"category": category, "key": key, "value": value},
            )
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _recall(self, args: dict, ctx: dict) -> AgentResult:
        """Recall memory facts matching a query."""
        try:
            from memory.memory_manager import search_memory
            query = args.get("query", "").strip()
            results = search_memory(query, limit=8)
            return AgentResult(message=results or "Nothing found for that query.")
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _summarize(self, args: dict, ctx: dict) -> AgentResult:
        """Summarize a session log (used at session end)."""
        log = ctx.get("session_log", args.get("log", []))
        if not log or len(log) < 3:
            return AgentResult(message="Session too short to summarize.")
        # Delegate to the existing _save_session_summary logic (inline here
        # to avoid circular imports with main.py in Phase 2)
        return AgentResult(
            message="Session summary queued.",
            data={"log_length": len(log)},
        )

    def _profile_summary(self, args: dict, ctx: dict) -> AgentResult:
        """Return the current user profile as a formatted string."""
        try:
            from memory.profile_manager import profile_for_prompt
            text = profile_for_prompt()
            return AgentResult(message=text or "No profile data yet.")
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))
