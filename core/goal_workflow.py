"""Automatic goal workflow: goal -> browser research -> starter plan.

This is intentionally deterministic and safe. It opens research tabs and saves
an editable starter plan; the LLM can refine it later through goal_tracker.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

GOALS_PATH = Path(__file__).resolve().parent.parent / "memory" / "goals.json"


def _load_goals() -> list[dict]:
    try:
        data = json.loads(GOALS_PATH.read_text(encoding="utf-8")) if GOALS_PATH.exists() else []
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_goals(goals: list[dict]) -> None:
    GOALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOALS_PATH.write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")


def _goal_type(subject: str, supplied: str = "") -> str:
    text = f"{subject} {supplied}".lower()
    if any(word in text for word in ("gate", "exam", "test", "certification", "entrance")):
        return "exam_preparation"
    if any(word in text for word in ("fitness", "workout", "running", "weight")):
        return "fitness"
    if any(word in text for word in ("learn", "study", "skill", "course")):
        return "learning"
    return "project"


def _starter_plan(subject: str, kind: str) -> dict:
    if kind == "exam_preparation":
        return {
            "milestones": [
                {"title": "Understand the syllabus", "tasks": [
                    {"title": "Collect the official syllabus", "status": "pending"},
                    {"title": "List subjects and their weightage", "status": "pending"},
                ]},
                {"title": "Measure the starting level", "tasks": [
                    {"title": "Take a diagnostic or previous-year paper", "status": "pending"},
                    {"title": "Record weak and strong topics", "status": "pending"},
                ]},
                {"title": "Build a weekly study routine", "tasks": [
                    {"title": "Choose realistic study hours", "status": "pending"},
                    {"title": "Start the first topic focus session", "status": "pending"},
                ]},
            ],
            "next_task": "Collect the official syllabus",
        }
    return {
        "milestones": [
            {"title": "Define the outcome", "tasks": [{"title": "Write a measurable success target", "status": "pending"}]},
            {"title": "Assess the starting point", "tasks": [{"title": "Complete a baseline check", "status": "pending"}]},
            {"title": "Start a weekly routine", "tasks": [{"title": "Schedule the first focused session", "status": "pending"}]},
        ],
        "next_task": "Define a measurable success target",
    }


def _queries(subject: str, kind: str) -> list[str]:
    if kind == "exam_preparation":
        return [
            f"{subject} official syllabus",
            f"{subject} important topics and subject weightage",
            f"{subject} previous year question papers",
            f"{subject} preparation strategy for beginners",
        ]
    return [
        f"{subject} roadmap for beginners",
        f"{subject} important topics",
        f"{subject} practice plan",
    ]


def _open_chrome_searches(queries: list[str]) -> bool:
    if os.name == "nt":
        # Start one Chrome process with multiple tabs when available.
        chrome_candidates = [
            os.environ.get("CHROME_PATH", ""),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome = next((p for p in chrome_candidates if p and Path(p).exists()), None)
        urls = ["https://www.google.com/search?q=" + quote_plus(q) for q in queries]
        if chrome:
            try:
                subprocess.Popen([chrome, *urls])
                return True
            except OSError:
                pass
    opened = False
    for query in queries:
        opened = webbrowser.open_new_tab("https://www.google.com/search?q=" + quote_plus(query)) or opened
    return opened


def start_goal_workflow(subject: str, goal_type: str | None = None) -> dict:
    """Research and seed a newly created goal using Universal Goal Intelligence Engine."""
    subject = re.sub(r"\s+", " ", (subject or "").strip())
    if not subject:
        return {"ok": False, "message": "No goal subject provided."}
    kind = goal_type or _goal_type(subject)
    
    try:
        from services.goal_intelligence_service import get_goal_intelligence_service
        g_service = get_goal_intelligence_service()
        intel_res = g_service.analyze_goal(subject, category=kind)
        return {
            "ok": True,
            "goal": subject,
            "goal_type": kind,
            "intelligence": intel_res
        }
    except Exception as exc:
        print(f"[GOAL_WORKFLOW] Goal intelligence analysis error: {exc}")
        return {"ok": False, "error": str(exc)}
