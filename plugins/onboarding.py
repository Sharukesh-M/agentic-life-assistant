"""Adaptive first-time onboarding for Jarvis-X.

The LLM decides when to call this plugin and extracts facts from natural speech;
this plugin persists them and returns the next useful question. It intentionally
avoids a rigid form and remains compatible with the existing PluginRegistry.
"""
from __future__ import annotations

from memory.profile_manager import load_profile, set_onboarding, update_profile

PLUGIN = {
    "name": "profile_onboarding",
    "description": (
        "Build and update the user's personalized Jarvis-X profile through natural conversation. "
        "Use on first interaction or when the user shares profile details. Ask only relevant follow-up "
        "questions. Actions: status, update, complete."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["status", "update", "complete"],
                "description": "Read onboarding status, save profile details, or mark onboarding complete.",
            },
            "preferred_name": {"type": "STRING", "description": "What Jarvis should call the user."},
            "user_type": {"type": "STRING", "description": "Student, professional, entrepreneur, freelancer, researcher, or another role."},
            "details": {"type": "OBJECT", "description": "Relevant details such as degree, branch, year, profession, goals, or preferences."},
            "next_question": {"type": "STRING", "description": "The next natural follow-up question, if one is needed."},
        },
        "required": ["action"],
    },
}


def _status_text() -> str:
    profile = load_profile()
    onboarding = profile.get("onboarding", {})
    status = onboarding.get("status", "not_started")
    name = (profile.get("identity") or {}).get("preferred_name")
    role = (profile.get("role") or {}).get("type")
    if status == "completed":
        return f"Your profile is set up{f', {name}' if name else ''}. I can personalize your goals and tasks now."
    if status == "in_progress":
        return f"Personalization is in progress{f', {name}' if name else ''}. Continue naturally from the last question."
    return "This is a first-time profile setup. Introduce yourself and ask what Jarvis should call the user."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = (parameters.get("action") or "status").strip().lower()
    try:
        if action == "status":
            result = _status_text()
        else:
            preferred_name = (parameters.get("preferred_name") or "").strip()
            user_type = (parameters.get("user_type") or "").strip()
            details = parameters.get("details") or {}
            updates = {}
            if preferred_name:
                updates.setdefault("identity", {})["preferred_name"] = preferred_name
            if user_type:
                updates.setdefault("role", {})["type"] = user_type
            if isinstance(details, dict) and details:
                section = "education" if any(k in details for k in ("school", "college", "university", "degree", "branch", "year", "semester", "subjects")) else "profession" if any(k in details for k in ("job", "industry", "company", "experience", "profession")) else "important_context"
                updates.setdefault(section, {}).update({str(k): v for k, v in details.items() if v not in (None, "", [])})
            if updates:
                update_profile(updates)
            next_question = (parameters.get("next_question") or "").strip()
            if action == "complete":
                set_onboarding("completed")
                result = "Your profile is ready. I will use it to personalize future assistance."
            else:
                set_onboarding("in_progress", next_question or None)
                result = "Profile details saved." + (f" Next: {next_question}" if next_question else " Continue with the most relevant follow-up question.")
        if player:
            try:
                player.write_log(f"JARVIS: {result}")
            except Exception:
                pass
        return result
    except Exception as exc:
        return f"Profile onboarding failed: {exc}"
