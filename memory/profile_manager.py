"""Structured user profile storage for Jarvis-X.

This complements (rather than replaces) long-term fact memory: facts remain in
memory/long_term.json, while profile fields and onboarding progress live in one
small, explicitly structured document.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


PROFILE_PATH = _base_dir() / "memory" / "profile.json"
_lock = Lock()


def _empty_profile() -> dict:
    return {
        "version": 1,
        "onboarding": {"status": "not_started", "last_question": None},
        "identity": {"preferred_name": None},
        "role": {"type": None, "details": {}},
        "education": {},
        "profession": {},
        "preferences": {},
        "interests": [],
        "skills": [],
        "important_context": {},
        "updated_at": None,
    }


def _merge(base: dict, incoming: dict) -> dict:
    for key, value in incoming.items():

        # Nested dictionaries → merge recursively
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)

        # Lists → append new items without duplicates
        elif isinstance(value, list) and isinstance(base.get(key), list):
            for item in value:
                if item not in base[key]:
                    base[key].append(item)

        # Normal values → replace existing value
        elif value is not None:
            base[key] = value

    return base


def load_profile() -> dict:
    with _lock:
        try:
            if PROFILE_PATH.exists():
                raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    return _merge(_empty_profile(), raw)
        except (OSError, ValueError, TypeError):
            pass
    return _empty_profile()


def save_profile(profile: dict) -> dict:
    data = _merge(_empty_profile(), profile if isinstance(profile, dict) else {})
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        PROFILE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def update_profile(updates: dict) -> dict:
    profile = load_profile()
    _merge(profile, updates if isinstance(updates, dict) else {})
    return save_profile(profile)


def set_onboarding(status: str, last_question: str | None = None) -> dict:
    if status not in {"not_started", "in_progress", "completed"}:
        status = "in_progress"
    return update_profile({"onboarding": {"status": status, "last_question": last_question}})


def onboarding_status() -> dict:
    return load_profile().get("onboarding", {})


def profile_for_prompt() -> str:
    """Return a compact context block safe to include in the system prompt."""
    p = load_profile()
    onboarding = p.get("onboarding", {})
    lines = [f"Onboarding status: {onboarding.get('status', 'not_started')}"]
    identity = p.get("identity", {})
    if identity.get("preferred_name"):
        lines.append(f"Preferred name: {identity['preferred_name']}")
    role = p.get("role", {})
    if role.get("type"):
        lines.append(f"User role: {role['type']}")
    for section in ("education", "profession", "preferences", "important_context"):
        values = p.get(section) or {}
        if values:
            compact = ", ".join(f"{k}={v}" for k, v in values.items())
            lines.append(f"{section.title()}: {compact[:500]}")
    for section in ("interests", "skills"):
        values = p.get(section) or []
        if values:
            lines.append(f"{section.title()}: {', '.join(map(str, values))[:500]}")
    return "[STRUCTURED PERSONAL PROFILE]\n" + "\n".join(lines)


def profile_for_ui() -> dict:
    return load_profile()
