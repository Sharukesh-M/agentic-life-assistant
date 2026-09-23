"""
goal_tracker.py — long-term goal memory for JARVIS
Drop into plugins/. Stores goals in memory/goals.json.

This is the piece that makes "I'm preparing for the GATE exam" stick as
an ongoing project rather than a one-off fact — create a goal once, then
log check-ins over time and ask for a status summary whenever you want.
Pair this with quiz_mode / flashcards for the actual study content, and
proactive.py can read goals.json to bring this up unprompted.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_PATH = Path(__file__).resolve().parent.parent / "memory" / "goals.json"

PLUGIN = {
    "name": "goal_tracker",
    "description": (
        "Remember an ongoing personal goal or project (like exam prep, "
        "learning a skill, fitness target), log progress check-ins on it "
        "over time, and give a status summary. Trigger phrases: 'I want to "
        "prepare for...', 'remember I'm working on...', 'how am I doing "
        "on...', 'log progress on...', 'what are my current goals'. This "
        "is for standing, multi-session goals — use todo_list for one-off "
        "tasks instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["create", "list", "checkin", "status", "update_context", "set_plan"],
                "description": "create/list/check in/status, update structured goal context, or save a generated plan.",
            },
            "subject": {
                "type": "STRING",
                "description": "The goal's subject, e.g. 'GATE exam' or 'learning Spanish' (required for 'create', 'checkin', 'status').",
            },
            "note": {"type": "STRING", "description": "Progress note text (required for 'checkin')."},
            "goal_type": {"type": "STRING", "description": "Goal category such as exam_preparation, learning, fitness, or project."},
            "metadata": {"type": "OBJECT", "description": "Known structured context for the goal; only include details the user provided."},
            "plan": {"type": "OBJECT", "description": "Generated milestones/tasks plan to save for this goal."},
        },
        "required": ["action"],
    },
}


def _load():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _save(goals):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(goals, indent=2), encoding="utf-8")


def _find(goals, subject):
    subject_lower = subject.strip().lower()
    return next((g for g in goals if g["subject"].lower() == subject_lower), None)


def _create(subject, goal_type=None):
    goals = _load()
    if _find(goals, subject):
        return f"You already have an active goal for '{subject}'."
    goal = {
        "id": uuid.uuid4().hex[:6],
        "subject": subject,
        "created": datetime.now().isoformat(),
        "status": "active",
        "checkins": [],
        "goal_type": goal_type or "project",
        "metadata": {},
        "plan": None,
    }
    goals.append(goal)
    _save(goals)
    return f"Got it — I'll remember you're working on '{subject}'. Let me know how it goes along the way."


def _list():
    goals = [g for g in _load() if g["status"] == "active"]
    if not goals:
        return "You don't have any active goals right now."
    lines = [f"{g['subject']} ({len(g['checkins'])} check-in(s))" for g in goals]
    return "Active goals: " + "; ".join(lines)


def _checkin(subject, note):
    goals = _load()
    goal = _find(goals, subject)
    if not goal:
        return f"I don't have a goal called '{subject}' — want me to create one?"
    goal["checkins"].append({"date": datetime.now().isoformat(), "note": note})
    _save(goals)
    return f"Logged on '{subject}': {note}"


def _status(subject):
    goals = _load()
    goal = _find(goals, subject)
    if not goal:
        return f"I don't have a goal called '{subject}'."
    created = datetime.fromisoformat(goal["created"])
    days_active = (datetime.now() - created).days
    n = len(goal["checkins"])
    if n == 0:
        return f"'{goal['subject']}' — started {days_active} day(s) ago, no check-ins logged yet."
    latest = goal["checkins"][-1]["note"]
    return f"'{goal['subject']}' — {days_active} day(s) active, {n} check-in(s). Latest: {latest}"


def _update_context(subject, metadata):
    goals = _load()
    goal = _find(goals, subject)
    if not goal:
        return f"I don't have a goal called '{subject}'."
    if isinstance(metadata, dict):
        goal.setdefault("metadata", {}).update({k: v for k, v in metadata.items() if v not in (None, "", [], {})})
    _save(goals)
    return f"Updated the context for '{goal['subject']}'."


def _set_plan(subject, plan):
    goals = _load()
    goal = _find(goals, subject)
    if not goal:
        return f"I don't have a goal called '{subject}'."
    if not isinstance(plan, dict):
        return "The plan must contain structured milestones or tasks."
    goal["plan"] = plan
    _save(goals)
    return f"Created an initial plan for '{goal['subject']}'."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    subject = parameters.get("subject")
    note = parameters.get("note")
    goal_type = parameters.get("goal_type")
    metadata = parameters.get("metadata")
    plan = parameters.get("plan")

    try:
        if action == "create":
            result_text = "What's the goal about?" if not subject else _create(subject, goal_type)
        elif action == "list":
            result_text = _list()
        elif action == "checkin":
            result_text = (
                "Which goal, and what should I log?" if not (subject and note) else _checkin(subject, note)
            )
        elif action == "status":
            result_text = "Which goal do you want a status on?" if not subject else _status(subject)
        elif action == "update_context":
            result_text = "Which goal should I update?" if not subject else _update_context(subject, metadata)
        elif action == "set_plan":
            result_text = "Which goal should receive the plan?" if not subject else _set_plan(subject, plan)
        else:
            result_text = f"Sir, I don't recognize the goal action '{action}'."
    except Exception as e:
        return f"Sir, goal_tracker plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text
