"""
agents/goal_agent.py - JARVIS-X Goal Agent

Phase 3 target: Wraps and extends the existing goal_tracker plugin and
core/personal_agent.py decision engine.

In Phase 2 this file defines the interface and stubs. The existing
plugins/goal_tracker.py remains the active implementation; this agent
layer will be activated by the Orchestrator in Phase 3.

Capabilities added over goal_tracker plugin:
  - pause / resume / abandon goals
  - prioritize across multiple concurrent goals
  - extended goal model: motivation, target_date, priority, constraints
  - progressive context discovery (no rigid questionnaire)
  - triggers PlanningAgent after sufficient context is collected
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.base_agent import AgentResult, BaseAgent


# ---------------------------------------------------------------------------
# GoalAgent
# ---------------------------------------------------------------------------

class GoalAgent(BaseAgent):
    """Manages user goals through their full lifecycle.

    Wraps plugins/goal_tracker.py (existing, unchanged) for storage and
    adds higher-level orchestration logic: prioritization, lifecycle
    transitions, and context-aware creation.
    """

    name = "goal_agent"
    description = (
        "Create, update, prioritize, pause, resume, and abandon goals. "
        "Supports multiple simultaneous goals. Uses progressive context "
        "discovery rather than rigid questionnaires."
    )
    capabilities = [
        "goal_management",
        "create_goal",
        "list_goals",
        "update_goal",
        "pause_goal",
        "resume_goal",
        "abandon_goal",
        "prioritize_goals",
        "goal_status",
        "decompose_goal",
    ]
    priority = 10

    _GOALS_PATH = (
        Path(__file__).resolve().parent.parent / "memory" / "goals.json"
    )

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        """Route to the appropriate goal operation based on intent."""
        tool_args = context.get("tool_args") or context
        action = tool_args.get("action", intent).lower().strip()

        dispatch = {
            "create":         self._create,
            "create_goal":    self._create,
            "list":           self._list,
            "list_goals":     self._list,
            "status":         self._status,
            "goal_status":    self._status,
            "checkin":        self._checkin,
            "update_context":  self._update_context,
            "set_plan":       self._set_plan,
            "pause":          self._pause,
            "pause_goal":     self._pause,
            "resume":         self._resume,
            "resume_goal":    self._resume,
            "abandon":        self._abandon,
            "abandon_goal":   self._abandon,
            "prioritize":     self._prioritize,
            "decompose":      self._decompose_goal,
            "decompose_goal": self._decompose_goal,
        }

        handler = dispatch.get(action, self._unknown)
        return handler(tool_args, context)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _load_goals(self) -> list[dict]:
        try:
            if self._GOALS_PATH.exists():
                data = json.loads(self._GOALS_PATH.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
        except Exception as exc:
            self._log_error(f"Load error: {exc}")
        return []

    def _save_goals(self, goals: list[dict]) -> None:
        try:
            self._GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._GOALS_PATH.write_text(
                json.dumps(goals, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            self._log_error(f"Save error: {exc}")

    def _find(self, goals: list[dict], subject: str) -> dict | None:
        subject_lower = subject.strip().lower()
        return next(
            (g for g in goals if g.get("subject", "").lower() == subject_lower),
            None,
        )

    # ── Operations ───────────────────────────────────────────────────────────

    def _create(self, args: dict, ctx: dict) -> AgentResult:
        # Delegate to existing goal_tracker plugin for storage compatibility
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(
                needs_input=True,
                missing_field="subject",
                message="What is the goal about?",
            )

        goals = self._load_goals()
        if self._find(goals, subject):
            return AgentResult(
                message=f"You already have an active goal for '{subject}'.",
                data={"exists": True, "subject": subject},
            )

        # Use existing goal_tracker plugin (preserves goals.json format)
        try:
            from plugins.goal_tracker import run as gt_run
            result_text = gt_run(args, player=None, session_memory=None)
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

        self._log_info(f"Created goal: {subject}")

        # Phase 4 Enhancement: Auto-run workflow & seed tasks into TaskStore
        goal_type = args.get("goal_type")
        wf_res = {}
        try:
            from core.goal_workflow import start_goal_workflow
            wf_res = start_goal_workflow(subject, goal_type)
        except Exception as exc:
            self._log_error(f"Goal workflow error: {exc}")

        # Seed tasks into TaskStore via PlanningAgent
        tasks_msg = ""
        try:
            from agents.planning_agent import PlanningAgent
            planning = PlanningAgent()
            task_res = planning.handle("create_tasks", {"action": "create_tasks", "subject": subject})
            if task_res.success:
                tasks_msg = task_res.message
        except Exception as exc:
            self._log_error(f"Task seeding error: {exc}")

        msg = f"{result_text}\n\nStarted starter plan and research for '{subject}'."
        if tasks_msg:
            msg += f"\n{tasks_msg}"

        return AgentResult(
            message=msg,
            data={"created": True, "subject": subject, "workflow": wf_res, "tasks_seeded": bool(tasks_msg)},
            next_agent="planning_agent",
        )

    def _decompose_goal(self, args: dict, ctx: dict) -> AgentResult:
        """Decompose a goal into specific milestones and seed tasks into TaskStore."""
        subject = args.get("subject", "").strip()
        milestones_input = args.get("milestones", [])
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject", message="Which goal do you want to decompose?")

        goals = self._load_goals()
        goal = self._find(goals, subject)
        if not goal:
            return AgentResult(success=False, error=f"Goal '{subject}' not found.")

        if not milestones_input:
            try:
                from core.goal_workflow import _starter_plan, _goal_type
                kind = goal.get("goal_type") or _goal_type(subject)
                plan = _starter_plan(subject, kind)
                milestones = plan.get("milestones", [])
            except Exception:
                milestones = [{"title": "Phase 1: Foundation", "tasks": [{"title": f"Initial research for {subject}"}]}]
        else:
            milestones = milestones_input

        goal["plan"] = {"milestones": milestones}
        self._save_goals(goals)

        # Seed tasks into TaskStore
        from memory.task_store import Task, TaskStatus, get_task_store
        store = get_task_store()
        created = []
        for ms in milestones:
            ms_title = ms.get("title", "Milestone") if isinstance(ms, dict) else str(ms)
            tasks_list = ms.get("tasks", []) if isinstance(ms, dict) else []
            if not tasks_list:
                tasks_list = [{"title": f"Work on {ms_title}"}]
            for t_spec in tasks_list:
                t_title = t_spec.get("title", ms_title) if isinstance(t_spec, dict) else str(t_spec)
                task = Task(
                    goal_id=goal.get("id", ""),
                    goal_subject=subject,
                    title=t_title,
                    status=TaskStatus.PENDING,
                    duration_minutes=45,
                )
                created.append(store.create(task))

        return AgentResult(
            message=f"Decomposed goal '{subject}' into {len(milestones)} milestone(s) and created {len(created)} task(s).",
            data={"milestones": milestones, "tasks_created": [t.to_dict() for t in created]},
        )

    def _list(self, args: dict, ctx: dict) -> AgentResult:
        goals = [g for g in self._load_goals() if g.get("status", "active") == "active"]
        if not goals:
            return AgentResult(message="No active goals right now.")
        lines = []
        for g in goals:
            priority = g.get("priority", 0)
            pstr = " [HIGH]" if priority > 0 else (" [LOW]" if priority < 0 else "")
            lines.append(f"- {g['subject']}{pstr} ({len(g.get('checkins', []))} check-ins)")
        return AgentResult(
            message="Active goals:\n" + "\n".join(lines),
            data={"goals": [g["subject"] for g in goals]},
        )

    def _status(self, args: dict, ctx: dict) -> AgentResult:
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject",
                               message="Which goal?")
        try:
            from plugins.goal_tracker import run as gt_run
            text = gt_run({"action": "status", "subject": subject})
            return AgentResult(message=text)
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _checkin(self, args: dict, ctx: dict) -> AgentResult:
        try:
            from plugins.goal_tracker import run as gt_run
            text = gt_run(args)
            return AgentResult(message=text)
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _update_context(self, args: dict, ctx: dict) -> AgentResult:
        try:
            from plugins.goal_tracker import run as gt_run
            text = gt_run(args)
            return AgentResult(message=text)
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _set_plan(self, args: dict, ctx: dict) -> AgentResult:
        try:
            from plugins.goal_tracker import run as gt_run
            text = gt_run(args)
            return AgentResult(message=text)
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    def _pause(self, args: dict, ctx: dict) -> AgentResult:
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject",
                               message="Which goal should I pause?")
        goals = self._load_goals()
        goal = self._find(goals, subject)
        if not goal:
            return AgentResult(success=False,
                               error=f"No goal named '{subject}' found.")
        goal["status"] = "paused"
        self._save_goals(goals)
        return AgentResult(
            message=f"Got it — '{subject}' is paused. I'll keep it in your goals list.",
            data={"paused": subject},
        )

    def _resume(self, args: dict, ctx: dict) -> AgentResult:
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject",
                               message="Which goal should I resume?")
        goals = self._load_goals()
        goal = self._find(goals, subject)
        if not goal:
            return AgentResult(success=False,
                               error=f"No goal named '{subject}' found.")
        goal["status"] = "active"
        self._save_goals(goals)
        return AgentResult(
            message=f"'{subject}' is active again.",
            data={"resumed": subject},
        )

    def _abandon(self, args: dict, ctx: dict) -> AgentResult:
        subject = args.get("subject", "").strip()
        if not subject:
            return AgentResult(needs_input=True, missing_field="subject",
                               message="Which goal should I mark as abandoned?")
        goals = self._load_goals()
        goal = self._find(goals, subject)
        if not goal:
            return AgentResult(success=False,
                               error=f"No goal named '{subject}' found.")
        goal["status"] = "abandoned"
        self._save_goals(goals)
        return AgentResult(
            message=f"Okay — '{subject}' has been marked as abandoned.",
            data={"abandoned": subject},
        )

    def _prioritize(self, args: dict, ctx: dict) -> AgentResult:
        """Reorder goals by priority. args may contain a priority list."""
        ordered = args.get("order", [])  # list of subjects, highest first
        if not ordered:
            return self._list(args, ctx)
        goals = self._load_goals()
        for idx, subject in enumerate(ordered):
            goal = self._find(goals, subject)
            if goal:
                goal["priority"] = len(ordered) - idx  # highest first = highest number
        self._save_goals(goals)
        return AgentResult(
            message="Goal priorities updated: " + " > ".join(ordered),
            data={"prioritized": ordered},
        )

    def _unknown(self, args: dict, ctx: dict) -> AgentResult:
        action = args.get("action", "unknown")
        return AgentResult(
            success=False,
            error=f"Unknown goal action: '{action}'",
        )
