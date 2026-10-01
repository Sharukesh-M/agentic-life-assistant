"""
agents/proactive_agent.py - JARVIS-X Proactive Agent

Extends the existing ProactiveEngine (actions/proactive.py) with
goal, task, and progress awareness.

The existing ProactiveEngine handles: timing, memory context, rotation.
This agent adds: pending tasks for today, skip patterns, upcoming deadlines.
"""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentResult, BaseAgent


class ProactiveAgent(BaseAgent):
    """Goal-aware proactive check-in builder.

    Wraps actions/proactive.py (unchanged) and enriches its prompt with:
    - Tasks scheduled for today
    - Tasks overdue
    - Skip patterns detected
    - Upcoming goal milestones
    """

    name = "proactive_agent"
    description = (
        "Generate context-rich proactive check-in prompts that are aware of "
        "today's tasks, skip patterns, and goal deadlines."
    )
    capabilities = [
        "proactive_assistance",
        "proactive_check",
        "build_proactive_prompt",
        "task_reminder",
        "goal_nudge",
    ]
    priority = 6

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args", {})
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "build_proactive_prompt": self._build_prompt,
            "task_reminder":          self._task_reminder,
            "goal_nudge":             self._goal_nudge,
        }
        handler = dispatch.get(action, self._build_prompt)
        return handler(args, context)

    def _build_prompt(self, args: dict, ctx: dict) -> AgentResult:
        """Build an enriched proactive prompt for Gemini."""
        memory = ctx.get("memory", {})
        session_log = ctx.get("session_log", [])

        # Gather task context
        task_ctx = self._get_task_context()
        skip_ctx = self._get_skip_context()

        # Use the existing ProactiveEngine for the base prompt
        try:
            from actions.proactive import ProactiveEngine
            import time
            engine = ProactiveEngine()
            engine.mark_triggered()   # update rotation
            base_prompt = engine.build_prompt(
                memory=memory,
                recent_turns=session_log[-6:] if session_log else None,
            )
        except Exception as exc:
            base_prompt = f"[PROACTIVE_CHECK] Proactive check-in.\n{exc}"

        # Enrich with task and skip awareness
        enrichment_parts = []
        if task_ctx:
            enrichment_parts.append(f"\nTask context:\n{task_ctx}")
        if skip_ctx:
            enrichment_parts.append(f"\nPattern observation (mention only if relevant):\n{skip_ctx}")

        enriched = base_prompt + "\n".join(enrichment_parts)
        return AgentResult(message=enriched)

    def _task_reminder(self, args: dict, ctx: dict) -> AgentResult:
        """Return today's tasks as a formatted reminder string."""
        task_ctx = self._get_task_context()
        if not task_ctx:
            return AgentResult(message="No tasks scheduled for today.")
        return AgentResult(message=f"Today's tasks:\n{task_ctx}")

    def _goal_nudge(self, args: dict, ctx: dict) -> AgentResult:
        """Identify the highest-priority pending goal and suggest working on it."""
        try:
            import json
            from pathlib import Path
            goals_path = Path(__file__).resolve().parent.parent / "memory" / "goals.json"
            goals = []
            if goals_path.exists():
                data = json.loads(goals_path.read_text(encoding="utf-8"))
                goals = [g for g in (data if isinstance(data, list) else [])
                         if g.get("status", "active") == "active"]
            if not goals:
                return AgentResult(message="No active goals to nudge about.")
            # Pick highest priority goal
            best = max(goals, key=lambda g: g.get("priority", 0))
            return AgentResult(
                message=f"Your highest-priority active goal is '{best['subject']}'.",
                data={"goal_subject": best["subject"]},
            )
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    # ── Context helpers ──────────────────────────────────────────────────────

    def _get_task_context(self) -> str:
        """Return a formatted string of today's pending tasks."""
        try:
            from memory.task_store import get_task_store
            store = get_task_store()
            today_tasks = store.today()
            pending = [t for t in today_tasks if t.status == "pending"]
            if not pending:
                return ""
            lines = [f"• [{t.goal_subject}] {t.title} (~{t.duration_minutes}min)"
                     for t in pending[:4]]
            return "\n".join(lines)
        except Exception:
            return ""

    def _get_skip_context(self) -> str:
        """Return skip pattern observations for proactive context."""
        try:
            import json
            from pathlib import Path
            from memory.task_store import get_task_store
            goals_path = Path(__file__).resolve().parent.parent / "memory" / "goals.json"
            goals = []
            if goals_path.exists():
                data = json.loads(goals_path.read_text(encoding="utf-8"))
                goals = [g for g in (data if isinstance(data, list) else [])
                         if g.get("status", "active") == "active"]

            store = get_task_store()
            patterns = []
            for g in goals:
                p = store.skip_pattern(g.get("id", ""))
                if p["has_pattern"]:
                    patterns.append(p["suggestion"])
            return "\n".join(patterns[:2])   # limit to 2 patterns
        except Exception:
            return ""
