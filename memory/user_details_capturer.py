"""
memory/user_details_capturer.py - Captures and persists user profile, goals, and learning memory.

Guarantees immediate synchronization between user conversation inputs/actions and disk storage:
- memory/profile.json
- memory/goals.json
- memory/learning_progress.json / roadmaps.json / learning_sessions.json
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.profile_manager import load_profile, save_profile, update_profile
from memory.learning_store import get_learning_store


def _base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


GOALS_PATH = _base_dir() / "memory" / "goals.json"


def capture_user_profile_details(
    preferred_name: Optional[str] = None,
    user_type: Optional[str] = None,
    target_exam: Optional[str] = None,
    subjects: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Captures and immediately persists structured user profile attributes to profile.json."""
    updates: Dict[str, Any] = {}

    if preferred_name:
        updates.setdefault("identity", {})["preferred_name"] = preferred_name

    if user_type:
        updates.setdefault("role", {})["type"] = user_type

    if target_exam:
        updates.setdefault("education", {})["target_exam"] = target_exam

    if subjects:
        updates["interests"] = list(set(subjects))
        updates.setdefault("education", {})["focus_areas"] = subjects

    if details:
        updates.setdefault("important_context", {}).update(details)

    res = update_profile(updates)
    print(f"[USER_DETAILS_CAPTURER] Persisted profile updates to profile.json: {list(updates.keys())}")
    return res


def capture_user_goal(
    subject: str,
    goal_type: str = "exam_prep",
    milestones: Optional[List[Dict[str, Any]]] = None,
    target_date: Optional[str] = None,
    priority: int = 1,
) -> Dict[str, Any]:
    """Captures and immediately persists a goal structure to memory/goals.json."""
    if not subject:
        return {}

    goals: List[Dict[str, Any]] = []
    if GOALS_PATH.exists():
        try:
            raw = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                goals = raw
        except Exception as exc:
            print(f"[USER_DETAILS_CAPTURER] Error loading goals.json: {exc}")

    subject_clean = subject.strip()
    existing = next((g for g in goals if g.get("subject", "").lower() == subject_clean.lower()), None)

    if not milestones:
        milestones = [
            {
                "title": f"Phase 1: {subject_clean} Fundamentals",
                "tasks": [f"Study core concepts of {subject_clean}", f"Practice 3 core problems"],
            },
            {
                "title": f"Phase 2: {subject_clean} Practice & Testing",
                "tasks": [f"Complete practice assessment for {subject_clean}"],
            },
        ]

    if not target_date:
        target_date = (date.today() + timedelta(days=30)).isoformat()

    if existing:
        existing["status"] = "active"
        existing["priority"] = priority
        existing["target_date"] = target_date
        existing["milestones"] = milestones
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        goal_record = existing
    else:
        goal_record = {
            "id": f"goal_{int(datetime.now().timestamp())}",
            "subject": subject_clean,
            "goal_type": goal_type,
            "status": "active",
            "priority": priority,
            "target_date": target_date,
            "milestones": milestones,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        goals.append(goal_record)

    GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOALS_PATH.write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[USER_DETAILS_CAPTURER] Persisted goal '{subject_clean}' to goals.json")
    return goal_record


def capture_learning_progress(
    subject: str,
    topics: Optional[List[str]] = None,
    minutes_spent: int = 0,
) -> Dict[str, Any]:
    """Captures and persists active learning progress, roadmaps, and sessions to memory/learning_progress.json."""
    store = get_learning_store()
    prog = store.load_progress()

    if minutes_spent > 0:
        prog["total_learning_minutes"] = prog.get("total_learning_minutes", 0) + minutes_spent

    if topics:
        strong = prog.get("strong_topics", [])
        for t in topics:
            if t not in strong:
                strong.append(t)
        prog["strong_topics"] = strong

    prog["last_active_date"] = date.today().isoformat()
    prog["active_learning_plan"] = {
        "subject": subject,
        "topics": topics or ["Fundamentals", "Practice Problems", "Review"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    store.save_progress(prog)

    # Also save a roadmap entry if none exists
    existing_rdm = store.get_roadmap_by_goal(subject)
    if not existing_rdm:
        store.save_roadmap({
            "title": f"Roadmap for {subject}",
            "goal_id": subject,
            "status": "in_progress",
            "modules": [
                {"module_id": f"mod_1", "title": f"{subject} Core Concepts", "status": "active", "topics": topics or []}
            ]
        })

    print(f"[USER_DETAILS_CAPTURER] Persisted learning progress for '{subject}' to learning_progress.json")
    return prog


def extract_and_persist_from_text(text: str) -> Dict[str, Any]:
    """Heuristically extracts user details, goals, and subjects from text turn and persists them immediately."""
    if not text:
        return {}

    captured = {}
    lower = text.lower()

    # Name extraction
    name_m = re.search(r"\b(my name is|i am|call me)\s+([A-Za-z]+)\b", text, re.IGNORECASE)
    if name_m and name_m.group(2).lower() not in {"preparing", "looking", "going", "doing", "studying"}:
        name = name_m.group(2).capitalize()
        capture_user_profile_details(preferred_name=name)
        captured["name"] = name

    # Placement / Exam / Goal extraction
    if any(k in lower for k in ["placement", "exam", "interview", "test", "gate", "aws", "python"]):
        subjects = []
        for kw in ["python", "dsa", "aptitude", "logical reasoning", "data structures", "algorithms", "sql"]:
            if kw in lower:
                subjects.append(kw.title() if len(kw) > 3 else kw.upper())

        exam_name = "Placement Preparation" if "placement" in lower else "General Exam"
        capture_user_profile_details(target_exam=exam_name, subjects=subjects)

        milestones = [
            {
                "title": "Python & Technical Fundamentals",
                "tasks": ["Revise Python fundamentals", "Solve 3 basic Python DSA problems"],
            },
            {
                "title": "Aptitude & Logical Reasoning",
                "tasks": ["Practice aptitude questions", "Logical reasoning set"],
            },
        ]
        capture_user_goal(subject=exam_name, goal_type="exam_prep", milestones=milestones)
        capture_learning_progress(subject=exam_name, topics=subjects or ["Python", "DSA"])
        captured["exam"] = exam_name
        captured["subjects"] = subjects

    return captured
