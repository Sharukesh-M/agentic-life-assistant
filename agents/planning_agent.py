"""
agents/planning_agent.py - JARVIS-X Planning Agent

Converts goals -> milestones -> daily tasks.
Considers deadlines, priorities, available time, dependencies,
skill level, and recent completion/skip patterns.

CRITICAL: The PlanningAgent generates SUGGESTIONS only.
It NEVER auto-applies a plan without user approval.
All plan changes go through the existing confirmation mechanism.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

from agents.base_agent import AgentResult, BaseAgent
from memory.task_store import Task, TaskStatus, get_task_store


# ---------------------------------------------------------------------------
# Plan data models
# ---------------------------------------------------------------------------

@dataclass
class TimeBlock:
    """One scheduled work block in a daily plan."""
    start_time: str             # "HH:MM"
    end_time: str               # "HH:MM"
    goal_subject: str
    task_title: str
    duration_minutes: int
    task_id: Optional[str] = None
    goal_id: Optional[str] = None
    is_break: bool = False

    def summary(self) -> str:
        label = "Break" if self.is_break else f"{self.goal_subject}: {self.task_title}"
        return f"{self.start_time}-{self.end_time}  {label}"


@dataclass
class DailyPlan:
    """A suggested daily schedule.

    The plan is returned to the LLM for presentation to the user.
    It is NOT applied automatically.
    """
    plan_date: str              # ISO date "YYYY-MM-DD"
    blocks: list[TimeBlock] = field(default_factory=list)
    goals_addressed: list[str] = field(default_factory=list)
    total_study_minutes: int = 0
    notes: list[str] = field(default_factory=list)
    needs_user_approval: bool = True

    def as_text(self) -> str:
        lines = [f"Suggested plan for {self.plan_date}:", ""]
        for block in self.blocks:
            lines.append(f"  {block.summary()}")
        if self.notes:
            lines.append("")
            for note in self.notes:
                lines.append(f"  Note: {note}")
        lines.append("")
        lines.append(f"Total study time: ~{self.total_study_minutes} minutes")
        lines.append("(This is a suggestion — let me know if you'd like changes.)")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "plan_date": self.plan_date,
            "blocks": [
                {
                    "start_time": b.start_time,
                    "end_time": b.end_time,
                    "goal_subject": b.goal_subject,
                    "task_title": b.task_title,
                    "duration_minutes": b.duration_minutes,
                    "is_break": b.is_break,
                }
                for b in self.blocks
            ],
            "goals_addressed": self.goals_addressed,
            "total_study_minutes": self.total_study_minutes,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# PlanningAgent
# ---------------------------------------------------------------------------

class PlanningAgent(BaseAgent):
    """Generates daily/weekly task plans from goals.

    Works with:
        - goals.json (via goal_tracker)
        - memory/tasks.json (via TaskStore)
        - User schedule constraints (from context)

    Never auto-applies plans. Always returns suggestions for user approval.
    """

    name = "planning_agent"
    description = (
        "Generate concrete daily task schedules from active goals. "
        "Considers deadlines, priorities, available time, and skip patterns. "
        "Returns suggestions for user approval, never auto-applies."
    )
    capabilities = [
        "task_planning",
        "daily_plan",
        "create_tasks",
        "schedule_tasks",
        "generate_plan",
        "create_daily_plan",
        "weekly_plan",
    ]
    priority = 8

    _GOALS_PATH = Path(__file__).resolve().parent.parent / "memory" / "goals.json"

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args") or context
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "daily_plan":         self._daily_plan,
            "create_daily_plan":  self._daily_plan,
            "generate_plan":      self._daily_plan,
            "create_tasks":       self._create_tasks_for_goal,
            "task_status":        self._task_status,
            "adaptive_review":    self._adaptive_review,
        }
        handler = dispatch.get(action, self._daily_plan)
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

    # ── Daily plan ───────────────────────────────────────────────────────────

    def _daily_plan(self, args: dict, ctx: dict) -> AgentResult:
        """Generate a suggested daily plan for all active goals."""
        goals = self._load_active_goals()
        if not goals:
            return AgentResult(
                message="No active goals to plan for. Create a goal first.",
                needs_input=True,
                missing_field="goal",
            )

        # Extract schedule constraints from args or context memory
        constraints = args.get("constraints", {})
        available_from = constraints.get("available_from", "16:00")
        available_until = constraints.get("available_until", "22:00")
        break_minutes = constraints.get("break_minutes", 15)

        plan_date = args.get("date", date.today().isoformat())
        store = get_task_store()

        # Check for skip patterns — note them as plan hints
        skip_notes = []
        for goal in goals:
            goal_id = goal.get("id", "")
            if goal_id:
                pattern = store.skip_pattern(goal_id)
                if pattern["has_pattern"]:
                    skip_notes.append(
                        f"{goal['subject']}: {pattern['suggestion']}"
                    )

        # Build time blocks (simple round-robin across goals by priority)
        sorted_goals = sorted(goals, key=lambda g: g.get("priority", 0), reverse=True)
        blocks: list[TimeBlock] = []
        goals_addressed: list[str] = []
        total_minutes = 0

        # Parse available window
        try:
            start_h, start_m = map(int, available_from.split(":"))
            end_h, end_m = map(int, available_until.split(":"))
            current_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
        except Exception:
            current_minutes = 16 * 60
            end_minutes = 22 * 60

        session_length = 45  # minutes per study block
        goal_idx = 0

        while current_minutes + session_length <= end_minutes and goal_idx < len(sorted_goals) * 3:
            g = sorted_goals[goal_idx % len(sorted_goals)]
            goal_idx += 1

            start_str = f"{current_minutes // 60:02d}:{current_minutes % 60:02d}"
            current_minutes += session_length
            end_str = f"{current_minutes // 60:02d}:{current_minutes % 60:02d}"

            # Get next pending task for this goal, or generate a generic one
            pending = store.pending(goal_id=g.get("id", ""))
            if not pending and g.get("subject"):
                self._create_tasks_for_goal({"subject": g["subject"]}, ctx)
                pending = store.pending(goal_id=g.get("id", ""))

            if pending:
                task = pending[0]
                task_title = task.title
                task_id = task.id
            else:
                task_title = f"Continue: {g['subject']}"
                task_id = None

            blocks.append(TimeBlock(
                start_time=start_str,
                end_time=end_str,
                goal_subject=g["subject"],
                task_title=task_title,
                duration_minutes=session_length,
                task_id=task_id,
                goal_id=g.get("id"),
            ))

            if g["subject"] not in goals_addressed:
                goals_addressed.append(g["subject"])
            total_minutes += session_length

            # Add a break between blocks if there's room
            if break_minutes > 0 and current_minutes + break_minutes + session_length <= end_minutes:
                break_end = current_minutes + break_minutes
                blocks.append(TimeBlock(
                    start_time=end_str,
                    end_time=f"{break_end // 60:02d}:{break_end % 60:02d}",
                    goal_subject="",
                    task_title="Break",
                    duration_minutes=break_minutes,
                    is_break=True,
                ))
                current_minutes = break_end

        plan = DailyPlan(
            plan_date=plan_date,
            blocks=blocks,
            goals_addressed=goals_addressed,
            total_study_minutes=total_minutes,
            notes=skip_notes,
        )

        return AgentResult(
            message=plan.as_text(),
            data=plan.to_dict(),
            needs_input=True,   # always needs approval
        )

    def _create_tasks_for_goal(self, args: dict, ctx: dict) -> AgentResult:
        """Create initial tasks for a newly created goal."""
        goals = self._load_active_goals()
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject",
                               message="Which goal should I create tasks for?")

        goal = next((g for g in goals if g.get("subject", "").lower() == subject.lower()), None)
        if not goal:
            return AgentResult(success=False, error=f"Goal '{subject}' not found.")

        plan = goal.get("plan", {})
        milestones = plan.get("milestones", [])
        store = get_task_store()
        created: list[Task] = []

        for ms in milestones[:2]:   # start with first 2 milestones
            for task_spec in ms.get("tasks", [])[:2]:  # max 2 tasks per milestone
                task = Task(
                    goal_id=goal.get("id", ""),
                    goal_subject=subject,
                    title=task_spec.get("title", "Task"),
                    status=TaskStatus.PENDING,
                    duration_minutes=45,
                )
                created.append(store.create(task))

        if created:
            return AgentResult(
                message=(
                    f"Created {len(created)} initial task(s) for '{subject}': "
                    + "; ".join(t.title for t in created[:3])
                ),
                data={"tasks_created": [t.to_dict() for t in created]},
            )
        return AgentResult(
            message=f"No milestone tasks found for '{subject}' — run goal workflow first.",
        )

    def _task_status(self, args: dict, ctx: dict) -> AgentResult:
        """Report task completion status for all goals."""
        goals = self._load_active_goals()
        store = get_task_store()
        lines = []
        for g in goals:
            stats = store.goal_stats(g.get("id", ""))
            if stats["total"] > 0:
                lines.append(
                    f"{g['subject']}: {stats['completed']}/{stats['total']} completed "
                    f"({int(stats['completion_rate'] * 100)}%)"
                )
        if not lines:
            return AgentResult(message="No task data yet. Create goals and tasks first.")
        return AgentResult(
            message="Task progress:\n" + "\n".join(lines),
            data={"stats": lines},
        )

    def _adaptive_review(self, args: dict, ctx: dict) -> AgentResult:
        """Review skip patterns and suggest schedule adjustments."""
        goals = self._load_active_goals()
        store = get_task_store()
        suggestions = []
        for g in goals:
            pattern = store.skip_pattern(g.get("id", ""))
            if pattern["has_pattern"]:
                suggestions.append(f"{g['subject']}: {pattern['suggestion']}")

        if not suggestions:
            return AgentResult(
                message="Great consistency! No persistent skip patterns detected."
            )
        message = (
            "I noticed some patterns in your task completion:\n\n"
            + "\n".join(f"• {s}" for s in suggestions)
            + "\n\nWould you like me to adjust the schedule?"
        )
        return AgentResult(
            message=message,
            data={"suggestions": suggestions},
            needs_input=True,
        )
