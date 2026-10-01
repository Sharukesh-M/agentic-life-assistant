"""
agents/progress_agent.py - JARVIS-X Progress Agent

Tracks task/goal progress over time. Detects skip patterns.
Reports non-judgmentally. Suggests (never forces) adjustments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.base_agent import AgentResult, BaseAgent
from memory.task_store import get_task_store


# ---------------------------------------------------------------------------
# ProgressReport
# ---------------------------------------------------------------------------

@dataclass
class ProgressReport:
    """Structured progress summary for one goal."""
    goal_subject: str
    total_tasks: int = 0
    completed: int = 0
    skipped: int = 0
    pending: int = 0
    completion_rate: float = 0.0
    has_skip_pattern: bool = False
    skip_suggestion: str = ""
    recent_completed: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [f"Progress on '{self.goal_subject}':"]
        lines.append(
            f"  Completed {self.completed} of {self.total_tasks} tasks "
            f"({int(self.completion_rate * 100)}%)"
        )
        if self.skipped > 0:
            lines.append(f"  {self.skipped} task(s) skipped")
        if self.pending > 0:
            lines.append(f"  {self.pending} task(s) still pending")
        if self.recent_completed:
            lines.append(f"  Recently done: {', '.join(self.recent_completed[:3])}")
        if self.has_skip_pattern and self.skip_suggestion:
            lines.append(f"  Observation: {self.skip_suggestion}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ProgressAgent
# ---------------------------------------------------------------------------

class ProgressAgent(BaseAgent):
    """Tracks and reports progress across all active goals.

    Never judges the user. Uses data to improve future planning, not to
    criticize past behavior.
    """

    name = "progress_agent"
    description = (
        "Track completed and skipped tasks, detect patterns, report progress "
        "non-judgmentally, and surface useful observations to improve planning."
    )
    capabilities = [
        "progress_tracking",
        "goal_progress",
        "task_completion",
        "skip_pattern",
        "weekly_review",
        "progress_report",
    ]
    priority = 7

    _GOALS_PATH = Path(__file__).resolve().parent.parent / "memory" / "goals.json"

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args") or context
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "progress_report":  self._report,
            "goal_progress":    self._report,
            "weekly_review":    self._weekly_review,
            "skip_pattern":     self._skip_pattern_report,
            "complete_task":    self._complete_task,
            "skip_task":        self._skip_task,
        }
        handler = dispatch.get(action, self._report)
        return handler(args, context)

    # ── Load active goals ────────────────────────────────────────────────────

    def _load_active_goals(self) -> list[dict]:
        try:
            if self._GOALS_PATH.exists():
                data = json.loads(self._GOALS_PATH.read_text(encoding="utf-8"))
                return [g for g in (data if isinstance(data, list) else [])
                        if g.get("status", "active") == "active"]
        except Exception:
            pass
        return []

    # ── Operations ───────────────────────────────────────────────────────────

    def _report(self, args: dict, ctx: dict) -> AgentResult:
        """Progress report across all active goals."""
        goals = self._load_active_goals()
        store = get_task_store()

        subject_filter = args.get("subject", "").strip()
        if subject_filter:
            goals = [g for g in goals
                     if g.get("subject", "").lower() == subject_filter.lower()]

        if not goals:
            return AgentResult(message="No active goals to report on.")

        reports: list[ProgressReport] = []
        for g in goals:
            stats = store.goal_stats(g.get("id", ""))
            pattern = store.skip_pattern(g.get("id", ""))
            recent_done = [
                t.title for t in store.completed(g.get("id", ""))[-3:]
            ]
            reports.append(ProgressReport(
                goal_subject=g["subject"],
                total_tasks=stats["total"],
                completed=stats["completed"],
                skipped=stats["skipped"],
                pending=stats["pending"],
                completion_rate=stats["completion_rate"],
                has_skip_pattern=pattern["has_pattern"],
                skip_suggestion=pattern["suggestion"],
                recent_completed=recent_done,
            ))

        text = "\n\n".join(r.as_text() for r in reports)
        return AgentResult(
            message=text,
            data={"reports": [r.__dict__ for r in reports]},
        )

    def _weekly_review(self, args: dict, ctx: dict) -> AgentResult:
        """A weekly summary with observations and adaptive suggestions."""
        goals = self._load_active_goals()
        store = get_task_store()
        sections = []
        suggestions = []

        for g in goals:
            stats = store.goal_stats(g.get("id", ""))
            pattern = store.skip_pattern(g.get("id", ""), window_days=7)
            completed = stats.get("completed", 0)
            total = stats.get("total", 0)

            if total == 0:
                continue

            if completed == total:
                sections.append(f"✓ {g['subject']}: All {total} tasks completed.")
            else:
                remaining = total - completed
                sections.append(
                    f"• {g['subject']}: {completed}/{total} done, "
                    f"{remaining} pending."
                )

            if pattern["has_pattern"]:
                suggestions.append(f"{g['subject']}: {pattern['suggestion']}")

        if not sections:
            return AgentResult(message="No task data found for the weekly review.")

        text = "Weekly review:\n\n" + "\n".join(sections)
        if suggestions:
            text += "\n\nObservations:\n" + "\n".join(f"• {s}" for s in suggestions)
            text += "\n\nWould you like me to suggest schedule adjustments?"

        return AgentResult(message=text, data={"suggestions": suggestions})

    def _skip_pattern_report(self, args: dict, ctx: dict) -> AgentResult:
        """Report skip patterns only, for proactive assistance context."""
        goals = self._load_active_goals()
        store = get_task_store()
        patterns = []
        for g in goals:
            p = store.skip_pattern(g.get("id", ""))
            if p["has_pattern"]:
                patterns.append({
                    "subject":    g["subject"],
                    "skips":      p["consecutive_skips"],
                    "time_slot":  p["most_skipped_time"],
                    "suggestion": p["suggestion"],
                })
        if not patterns:
            return AgentResult(message="No persistent skip patterns detected.")
        msg = "\n".join(
            f"• {p['subject']}: {p['suggestion']}" for p in patterns
        )
        return AgentResult(message=msg, data={"patterns": patterns})

    def _complete_task(self, args: dict, ctx: dict) -> AgentResult:
        """Mark a task as completed by ID or title match."""
        task_id = args.get("task_id", "").strip()
        title = args.get("title", "").strip()
        store = get_task_store()

        if task_id:
            task = store.get(task_id)
        elif title:
            results = store.search(title)
            task = results[0] if results else None
        else:
            return AgentResult(needs_input=True, missing_field="task_id",
                               message="Which task should I mark as done?")

        if not task:
            return AgentResult(success=False, error="Task not found.")

        task.complete()
        store.update(task.id, status=task.status, completed_at=task.completed_at,
                     updated_at=task.updated_at)

        # Sync check-in to goals.json
        if task.goal_subject:
            try:
                from plugins.goal_tracker import run as gt_run
                gt_run({"action": "checkin", "subject": task.goal_subject, "note": f"Completed task: {task.title}"})
            except Exception:
                pass

        stats = store.goal_stats(task.goal_id) if task.goal_id else {}
        completion_str = f" Progress on '{task.goal_subject}': {stats.get('completed', 0)}/{stats.get('total', 0)} tasks completed." if stats else ""

        return AgentResult(
            message=f"Task completed: '{task.title}'. Good work.{completion_str}",
            data={"task_id": task.id, "goal_subject": task.goal_subject, "stats": stats},
        )

    def _skip_task(self, args: dict, ctx: dict) -> AgentResult:
        """Mark a task as skipped."""
        task_id = args.get("task_id", "").strip()
        title = args.get("title", "").strip()
        reason = args.get("reason", "").strip()
        store = get_task_store()

        if task_id:
            task = store.get(task_id)
        elif title:
            results = store.search(title)
            task = results[0] if results else None
        else:
            return AgentResult(needs_input=True, missing_field="task_id",
                               message="Which task should I mark as skipped?")

        if not task:
            return AgentResult(success=False, error="Task not found.")

        task.skip(reason)
        store.update(task.id, status=task.status, skip_count=task.skip_count,
                     skip_reasons=task.skip_reasons, updated_at=task.updated_at)

        obs = ""
        if task.goal_id:
            pattern = store.skip_pattern(task.goal_id)
            if pattern.get("has_pattern"):
                obs = f"\nObservation: {pattern['suggestion']}"

        return AgentResult(
            message=f"Noted — '{task.title}' skipped.{obs}",
            data={"task_id": task.id, "skip_count": task.skip_count},
        )
