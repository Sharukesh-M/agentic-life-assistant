"""
memory/learning_store.py — Persistent Storage for JARVIS-X Learning Intelligence Engine

Persists roadmaps, curricula, lessons, quizzes, coding challenges, and progress records.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


def _base_dir() -> Path:
    return Path(__file__).resolve().parent


_MEMORY_DIR = _base_dir()
_lock = Lock()


class LearningStore:
    """Manages JSON persistence for learning artifacts."""

    def __init__(self, memory_dir: Optional[Path] = None):
        self.dir = memory_dir or _MEMORY_DIR
        self.roadmaps_path = self.dir / "roadmaps.json"
        self.lessons_path = self.dir / "lessons.json"
        self.quizzes_path = self.dir / "quizzes.json"
        self.coding_path = self.dir / "coding_challenges.json"
        self.progress_path = self.dir / "learning_progress.json"

    def _read_json(self, path: Path, default: Any) -> Any:
        with _lock:
            try:
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    return data
            except Exception as exc:
                print(f"[LearningStore] Error reading {path.name}: {exc}")
        return default

    def _write_json(self, path: Path, data: Any) -> None:
        with _lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:
                print(f"[LearningStore] Error writing {path.name}: {exc}")

    # --- Roadmaps ---
    def load_roadmaps(self) -> List[Dict[str, Any]]:
        return self._read_json(self.roadmaps_path, [])

    def save_roadmap(self, roadmap_data: Dict[str, Any]) -> Dict[str, Any]:
        roadmaps = self.load_roadmaps()
        rid = roadmap_data.get("roadmap_id") or roadmap_data.get("id")
        if not rid:
            rid = f"rdm-{int(datetime.now().timestamp())}"
            roadmap_data["roadmap_id"] = rid

        roadmap_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Replace existing or append
        updated = False
        for idx, item in enumerate(roadmaps):
            if item.get("roadmap_id") == rid or item.get("id") == rid:
                roadmaps[idx] = roadmap_data
                updated = True
                break
        if not updated:
            roadmaps.append(roadmap_data)

        self._write_json(self.roadmaps_path, roadmaps)
        return roadmap_data

    def get_roadmap_by_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        for item in self.load_roadmaps():
            if item.get("goal_id") == goal_id:
                return item
        return None

    def get_roadmap(self, roadmap_id: str) -> Optional[Dict[str, Any]]:
        for item in self.load_roadmaps():
            if item.get("roadmap_id") == roadmap_id or item.get("id") == roadmap_id:
                return item
        return None

    # --- Lessons ---
    def load_lessons(self) -> List[Dict[str, Any]]:
        return self._read_json(self.lessons_path, [])

    def save_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        lessons = self.load_lessons()
        lid = lesson_data.get("lesson_id") or lesson_data.get("id") or f"lsn-{int(datetime.now().timestamp())}"
        lesson_data["lesson_id"] = lid
        lesson_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated = False
        for idx, item in enumerate(lessons):
            if item.get("lesson_id") == lid:
                lessons[idx] = lesson_data
                updated = True
                break
        if not updated:
            lessons.append(lesson_data)

        self._write_json(self.lessons_path, lessons)
        return lesson_data

    # --- Quizzes ---
    def load_quizzes(self) -> List[Dict[str, Any]]:
        return self._read_json(self.quizzes_path, [])

    def save_quiz(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        quizzes = self.load_quizzes()
        qid = quiz_data.get("quiz_id") or quiz_data.get("id") or f"qz-{int(datetime.now().timestamp())}"
        quiz_data["quiz_id"] = qid

        updated = False
        for idx, item in enumerate(quizzes):
            if item.get("quiz_id") == qid:
                quizzes[idx] = quiz_data
                updated = True
                break
        if not updated:
            quizzes.append(quiz_data)

        self._write_json(self.quizzes_path, quizzes)
        return quiz_data

    # --- Coding Challenges ---
    def load_coding_challenges(self) -> List[Dict[str, Any]]:
        return self._read_json(self.coding_path, [])

    def save_coding_challenge(self, challenge_data: Dict[str, Any]) -> Dict[str, Any]:
        challenges = self.load_coding_challenges()
        cid = challenge_data.get("challenge_id") or challenge_data.get("id") or f"code-{int(datetime.now().timestamp())}"
        challenge_data["challenge_id"] = cid

        updated = False
        for idx, item in enumerate(challenges):
            if item.get("challenge_id") == cid:
                challenges[idx] = challenge_data
                updated = True
                break
        if not updated:
            challenges.append(challenge_data)

        self._write_json(self.coding_path, challenges)
        return challenge_data

    # --- Progress ---
    def load_progress(self) -> Dict[str, Any]:
        return self._read_json(self.progress_path, {
            "total_learning_minutes": 0,
            "completed_topics": [],
            "skipped_topics": [],
            "weak_topics": [],
            "strong_topics": [],
            "quiz_accuracy": {},
            "coding_accuracy": {},
            "streak_days": 0,
            "last_active_date": None
        })

    def save_progress(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        self._write_json(self.progress_path, progress_data)
        return progress_data


_store_instance: Optional[LearningStore] = None


def get_learning_store() -> LearningStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = LearningStore()
    return _store_instance
