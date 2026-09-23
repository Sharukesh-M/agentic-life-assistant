"""Dynamic personal-agent orchestration tool.

The model calls this after a user expresses an ongoing goal.

The agent:
- checks the saved user profile
- checks the active goal
- uses the latest user message
- avoids asking for information already known
- decides what should happen next
- does not use a rigid questionnaire
"""

from __future__ import annotations

import json
from pathlib import Path

from core.personal_agent import (
    choose_next_step,
    decision_for_prompt,
    infer_goal_type,
)

from memory.profile_manager import load_profile


# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------

GOALS_PATH = (
    Path(__file__).resolve().parent.parent
    / "memory"
    / "goals.json"
)


# -------------------------------------------------------------------
# Plugin definition
# -------------------------------------------------------------------

PLUGIN = {
    "name": "personal_agent",
    "description": (
        "Choose the next best conversational or execution step for "
        "an active personal goal. Use after a user expresses a "
        "long-term goal or asks how to progress. It checks saved "
        "profile and goal context, avoids repeating known information, "
        "returns one information need at most, and indicates when "
        "enough context exists to create a plan. It does not generate "
        "fixed questionnaire wording."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["next_step"],
                "description": (
                    "Choose the next best step for the active goal."
                ),
            },
            "subject": {
                "type": "STRING",
                "description": (
                    "Active goal subject, such as GATE preparation."
                ),
            },
            "user_message": {
                "type": "STRING",
                "description": (
                    "The user's latest goal-related message."
                ),
            },
        },
        "required": ["action", "subject"],
    },
}


# -------------------------------------------------------------------
# Load goals
# -------------------------------------------------------------------

def _goals() -> list[dict]:
    """Load saved goals from goals.json."""

    try:
        if GOALS_PATH.exists():
            data = json.loads(
                GOALS_PATH.read_text(encoding="utf-8")
            )

            if isinstance(data, list):
                return data

    except (OSError, ValueError, TypeError):
        pass

    return []


# -------------------------------------------------------------------
# Find active goal
# -------------------------------------------------------------------

def _find_goal(subject: str, goals: list[dict]) -> dict | None:
    """Find a goal by subject, case-insensitively."""

    subject = subject.strip().lower()

    for goal in goals:
        goal_subject = str(
            goal.get("subject", "")
        ).strip().lower()

        if goal_subject == subject:
            return goal

    return None


# -------------------------------------------------------------------
# Main plugin entry point
# -------------------------------------------------------------------

def run(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    """Choose the next step for an active personal goal."""

    parameters = parameters or {}

    # ---------------------------------------------------------------
    # Get subject
    # ---------------------------------------------------------------

    subject = (
        parameters.get("subject") or ""
    ).strip()

    if not subject:
        return (
            "I need the active goal subject before "
            "choosing the next step."
        )

    # ---------------------------------------------------------------
    # Load goals
    # ---------------------------------------------------------------

    goals = _goals()

    goal = _find_goal(
        subject,
        goals,
    )

    if not goal:
        return (
            f"No active goal named '{subject}' exists yet. "
            "Create it with goal_tracker first."
        )

    # ---------------------------------------------------------------
    # Latest user message
    # ---------------------------------------------------------------

    user_message = (
        parameters.get("user_message") or ""
    ).strip()

    # ---------------------------------------------------------------
    # Load structured profile
    # ---------------------------------------------------------------

    profile = load_profile()

    # ---------------------------------------------------------------
    # Infer goal type if missing
    # ---------------------------------------------------------------

    if not goal.get("goal_type"):
        goal["goal_type"] = infer_goal_type(
            subject,
            user_message,
        )

    # ---------------------------------------------------------------
    # Decide what should happen next
    # ---------------------------------------------------------------

    decision = choose_next_step(
        goal,
        profile,
        user_message,
    )

    # ---------------------------------------------------------------
    # Build result for Jarvis
    # ---------------------------------------------------------------

    result = {
        "action": decision.action,
        "reason": decision.reason,
        "missing": decision.missing,
        "instruction_for_jarvis": decision_for_prompt(
            decision
        ),
        "goal_type": goal.get("goal_type"),
    }

    return json.dumps(
        result,
        ensure_ascii=False,
    )