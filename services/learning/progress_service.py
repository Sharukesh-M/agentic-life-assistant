"""
services/learning/progress_service.py — Learning Progress Analytics & Weak Area Service

Tracks learning statistics, completion rates, quiz accuracy, and identifies weak vs strong areas.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store


class LearningProgressService:
    """Manages learning progress analytics, weak area tracking, and streak metrics."""

    def __init__(self):
        self.store = get_learning_store()

    def record_study_session(self, minutes: int, topic: str, accuracy: Optional[float] = None) -> Dict[str, Any]:
        """Records a completed study session and updates progress statistics."""
        progress = self.store.load_progress()
        progress["total_learning_minutes"] = progress.get("total_learning_minutes", 0) + minutes

        if accuracy is not None:
            progress["quiz_accuracy"][topic] = accuracy
            if accuracy >= 80.0:
                if topic not in progress["strong_topics"]:
                    progress["strong_topics"].append(topic)
                if topic in progress["weak_topics"]:
                    progress["weak_topics"].remove(topic)
                if topic not in progress["completed_topics"]:
                    progress["completed_topics"].append(topic)
            elif accuracy < 50.0:
                if topic not in progress["weak_topics"]:
                    progress["weak_topics"].append(topic)

        # Update streak
        today_str = datetime.now().strftime("%Y-%m-%d")
        last_active = progress.get("last_active_date")
        if last_active != today_str:
            progress["streak_days"] = progress.get("streak_days", 0) + 1
            progress["last_active_date"] = today_str

        self.store.save_progress(progress)
        return progress

    def get_progress_summary(self) -> Dict[str, Any]:
        """Returns comprehensive learning progress summary."""
        progress = self.store.load_progress()
        total_topics = len(progress.get("completed_topics", [])) + len(progress.get("weak_topics", [])) or 1
        completion_rate = round((len(progress.get("completed_topics", [])) / total_topics) * 100, 1)

        return {
            "total_learning_minutes": progress.get("total_learning_minutes", 0),
            "completed_topics_count": len(progress.get("completed_topics", [])),
            "completed_topics": progress.get("completed_topics", []),
            "weak_topics": progress.get("weak_topics", []),
            "strong_topics": progress.get("strong_topics", []),
            "completion_rate_percent": completion_rate,
            "streak_days": progress.get("streak_days", 0),
            "quiz_accuracy": progress.get("quiz_accuracy", {})
        }
