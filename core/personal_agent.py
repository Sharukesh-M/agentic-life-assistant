"""Dynamic personal-agent decision engine.

This module does not contain a questionnaire.

It:
- identifies the type of goal
- checks what information is already known
- uses both goal metadata and the structured user profile
- returns the next required operation
- prevents repeated questions
- lets the LLM phrase the actual response

The LLM is responsible for natural-language generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# -------------------------------------------------------------------
# Decision object
# -------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    missing: str | None = None
    context: dict[str, Any] | None = None


# -------------------------------------------------------------------
# Goal requirements
# -------------------------------------------------------------------
#
# These are INFORMATION REQUIREMENTS, not fixed questions.
#
# Example:
#
#   target      -> target date/year
#   scope       -> subjects/syllabus
#   availability -> study time
#
# The LLM decides how to ask for the information.
# -------------------------------------------------------------------

_GOAL_REQUIREMENTS = {

    "exam_preparation": (
        (
            "target",
            "target date/year",
            "needed to calculate the preparation window",
        ),
        (
            "scope",
            "exam subjects or syllabus",
            "needed to define milestones",
        ),
        (
            "availability",
            "realistic study availability",
            "needed to create a sustainable schedule",
        ),
        (
            "baseline",
            "current level or diagnostic result",
            "needed to choose the starting difficulty",
        ),
    ),

    "learning": (
        (
            "outcome",
            "desired learning outcome",
            "needed to define success",
        ),
        (
            "availability",
            "realistic weekly availability",
            "needed to create a schedule",
        ),
        (
            "baseline",
            "current skill level",
            "needed to choose the starting point",
        ),
    ),

    "fitness": (
        (
            "outcome",
            "desired outcome",
            "needed to define success",
        ),
        (
            "availability",
            "available time and routine",
            "needed to make the plan realistic",
        ),
        (
            "constraints",
            "relevant constraints",
            "needed to keep recommendations safe and practical",
        ),
    ),
}


# -------------------------------------------------------------------
# Goal type inference
# -------------------------------------------------------------------

def infer_goal_type(
    subject: str,
    message: str = "",
) -> str:
    """Infer a reusable goal category from the subject and latest message."""

    text = f"{subject} {message}".lower()

    # Exam / competitive examination
    if any(
        word in text
        for word in (
            "gate",
            "exam",
            "test",
            "certification",
            "entrance",
            "competitive exam",
        )
    ):
        return "exam_preparation"

    # Fitness
    if any(
        word in text
        for word in (
            "fitness",
            "workout",
            "run",
            "weight",
            "health",
        )
    ):
        return "fitness"

    # Learning
    if any(
        word in text
        for word in (
            "learn",
            "study",
            "skill",
            "course",
        )
    ):
        return "learning"

    return "project"


# -------------------------------------------------------------------
# Generic value check
# -------------------------------------------------------------------

_EMPTY_VALUES = (
    None,
    "",
    [],
    {},
)


def _has_value(value: Any) -> bool:
    """Return True when a value contains meaningful information."""

    if value in _EMPTY_VALUES:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    return True


# -------------------------------------------------------------------
# Aliases
# -------------------------------------------------------------------
#
# Different parts of Jarvis may store the same concept under
# slightly different names.
#
# Example:
#
# target -> target_date / target_year / deadline
#
# This lets the decision engine understand existing data without
# forcing every module to use exactly the same key.
# -------------------------------------------------------------------

_ALIASES = {

    "target": (
        "target",
        "target_date",
        "target_year",
        "deadline",
    ),

    "scope": (
        "scope",
        "subjects",
        "subject",
        "syllabus",
        "branch",
    ),

    "availability": (
        "availability",
        "available_hours",
        "hours_per_day",
        "study_time",
        "weekly_hours",
    ),

    "baseline": (
        "baseline",
        "current_level",
        "diagnostic_score",
        "experience",
        "current_skill",
    ),

    "outcome": (
        "outcome",
        "success_definition",
        "desired_outcome",
        "goal",
    ),

    "constraints": (
        "constraints",
        "limitations",
        "restrictions",
    ),
}


# -------------------------------------------------------------------
# Search a dictionary for a requirement
# -------------------------------------------------------------------

def _dict_has_requirement(
    data: dict[str, Any] | None,
    requirement: str,
) -> bool:

    if not isinstance(data, dict):
        return False

    aliases = _ALIASES.get(
        requirement,
        (requirement,),
    )

    for alias in aliases:
        if _has_value(data.get(alias)):
            return True

    return False


# -------------------------------------------------------------------
# Check whether a requirement exists
# -------------------------------------------------------------------

def _value_present(
    goal: dict,
    profile: dict,
    key: str,
) -> bool:
    """Check goal metadata and structured profile for known information."""

    # ---------------------------------------------------------------
    # 1. Goal metadata
    # ---------------------------------------------------------------

    metadata = goal.get("metadata") or {}

    if _dict_has_requirement(
        metadata,
        key,
    ):
        return True

    # ---------------------------------------------------------------
    # 2. Goal itself
    #
    # Some goal trackers may store values directly on the goal.
    # ---------------------------------------------------------------

    if _dict_has_requirement(
        goal,
        key,
    ):
        return True

    # ---------------------------------------------------------------
    # 3. Profile important context
    # ---------------------------------------------------------------

    important_context = (
        profile.get("important_context")
        or {}
    )

    if _dict_has_requirement(
        important_context,
        key,
    ):
        return True

    # ---------------------------------------------------------------
    # 4. Profile preferences
    # ---------------------------------------------------------------

    preferences = (
        profile.get("preferences")
        or {}
    )

    if _dict_has_requirement(
        preferences,
        key,
    ):
        return True

    # ---------------------------------------------------------------
    # 5. Education
    #
    # Useful for exam preparation / learning.
    # ---------------------------------------------------------------

    education = (
        profile.get("education")
        or {}
    )

    if _dict_has_requirement(
        education,
        key,
    ):
        return True

    # ---------------------------------------------------------------
    # 6. Profession
    # ---------------------------------------------------------------

    profession = (
        profile.get("profession")
        or {}
    )

    if _dict_has_requirement(
        profession,
        key,
    ):
        return True

    return False


# -------------------------------------------------------------------
# Detect whether the user has already provided the missing information
# in the latest message.
#
# This is intentionally lightweight.
#
# It prevents a situation like:
#
# Jarvis: "How many hours can you study?"
# User: "I can study 3 hours."
#
# from immediately being treated as if availability is still missing.
# -------------------------------------------------------------------

def _message_contains_requirement(
    user_message: str,
    key: str,
) -> bool:

    if not user_message:
        return False

    text = user_message.lower()

    if key == "target":
        return bool(
            re.search(
                r"\b20\d{2}\b",
                text,
            )
            or any(
                phrase in text
                for phrase in (
                    "this year",
                    "next year",
                    "target date",
                    "deadline",
                    "by june",
                    "by july",
                    "by august",
                    "by september",
                    "by october",
                    "by november",
                    "by december",
                )
            )
        )

    if key == "scope":
        return any(
            phrase in text
            for phrase in (
                "subjects",
                "syllabus",
                "branch",
                "computer science",
                "cse",
                "mathematics",
                "maths",
                "physics",
                "chemistry",
            )
        )

    if key == "availability":
        return bool(
            re.search(
                r"\b\d+(?:\.\d+)?\s*(?:hours?|hrs?)\b",
                text,
            )
            or any(
                phrase in text
                for phrase in (
                    "hours a day",
                    "hours per day",
                    "hours daily",
                    "every day",
                    "weekends",
                    "weekdays",
                    "free time",
                    "study time",
                )
            )
        )

    if key == "baseline":
        return any(
            phrase in text
            for phrase in (
                "beginner",
                "intermediate",
                "advanced",
                "weak in",
                "strong in",
                "good at",
                "bad at",
                "current level",
                "already know",
                "i know",
                "i don't know",
                "diagnostic",
                "score",
                "mock test",
            )
        )

    if key == "outcome":
        return any(
            phrase in text
            for phrase in (
                "i want to",
                "my goal is",
                "i want",
                "i need to",
                "learn",
                "master",
                "become",
                "prepare",
                "get better",
            )
        )

    if key == "constraints":
        return any(
            phrase in text
            for phrase in (
                "can't",
                "cannot",
                "unable",
                "limitation",
                "constraint",
                "injury",
                "restriction",
                "avoid",
            )
        )

    return False


# -------------------------------------------------------------------
# Main decision engine
# -------------------------------------------------------------------

def choose_next_step(
    goal: dict,
    profile: dict,
    user_message: str = "",
) -> Decision:
    """Return the next best operation, not a fixed sentence."""

    # ---------------------------------------------------------------
    # No goal
    # ---------------------------------------------------------------

    if not goal:
        return Decision(
            "normal_response",
            "There is no active goal to guide.",
        )

    # ---------------------------------------------------------------
    # Inactive goal
    # ---------------------------------------------------------------

    if goal.get("status") != "active":
        return Decision(
            "normal_response",
            "The goal is not active.",
        )

    # ---------------------------------------------------------------
    # Determine goal type
    # ---------------------------------------------------------------

    goal_type = (
        goal.get("goal_type")
        or infer_goal_type(
            goal.get("subject", ""),
            user_message,
        )
    )

    requirements = _GOAL_REQUIREMENTS.get(
        goal_type,
        (),
    )

    # ---------------------------------------------------------------
    # Check requirements
    # ---------------------------------------------------------------

    for key, label, reason in requirements:

        known = _value_present(
            goal,
            profile,
            key,
        )

        # Latest user message may already contain the answer.
        if not known:
            known = _message_contains_requirement(
                user_message,
                key,
            )

        if not known:

            return Decision(
                "ask_one_question",
                reason,
                missing=key,
                context={
                    "goal_type": goal_type,
                    "information_needed": label,
                },
            )

    # ---------------------------------------------------------------
    # Enough information → create plan
    # ---------------------------------------------------------------

    if not goal.get("plan"):

        return Decision(
            "create_plan",
            "The goal has enough context for an initial plan.",
            context={
                "goal_type": goal_type,
            },
        )

    # ---------------------------------------------------------------
    # Existing plan → execute next task
    # ---------------------------------------------------------------

    return Decision(
        "execute_next_task",
        "The goal has a plan; focus on the next incomplete task.",
        context={
            "goal_type": goal_type,
        },
    )


# -------------------------------------------------------------------
# Convert decision into LLM instruction
# -------------------------------------------------------------------

def decision_for_prompt(
    decision: Decision,
) -> str:
    """Give the LLM concise instructions for the next conversational move."""

    if decision.action == "ask_one_question":

        information_needed = (
            decision.context.get("information_needed")
            if decision.context
            else decision.missing
        )

        return (
            "Ask exactly ONE natural follow-up question. "
            "Phrase it yourself based on this information need: "
            f"{information_needed}. "
            f"Reason: {decision.reason}. "
            "Do not ask for information already known from the "
            "user profile, goal, or latest message."
        )

    if decision.action == "create_plan":

        return (
            "Stop collecting details. "
            "Create a useful first plan with milestones and tasks. "
            "Use the user's existing profile and goal context."
        )

    if decision.action == "execute_next_task":

        return (
            "The goal already has a plan. "
            "Recommend or start the next incomplete task. "
            "Use the existing goal context and do not restart onboarding."
        )

    return (
        "Respond normally unless the user asks for a goal action."
    )