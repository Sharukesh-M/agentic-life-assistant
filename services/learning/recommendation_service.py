"""
services/learning/recommendation_service.py — Personalized Next-Step Engine for JARVIS-X

Determines what the user should do next after any learning event:
CONTINUE, REVIEW, PRACTICE, QUIZ, CODE, ADVANCE, RETRY, REST, RESCHEDULE.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class LearningRecommendationService:
    """Evaluates progress and generates personalized next-step recommendations."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def get_next_step(self, user_context: Dict[str, Any], last_event: Optional[str] = None) -> Dict[str, Any]:
        """Determines the optimal next learning action for the user."""
        progress = self.store.load_progress()
        weak_topics = progress.get("weak_topics", [])
        completed = progress.get("completed_topics", [])

        # Priority 1: Address weak topics if struggling
        if weak_topics:
            topic = weak_topics[0]
            return {
                "action": "REVIEW",
                "title": f"Review & Reinforce: {topic}",
                "reason": f"Recent practice indicates room for improvement in {topic}.",
                "topic": topic,
                "estimated_minutes": 20
            }

        # Priority 2: Continue active roadmap or topic
        goal_title = user_context.get("current_goal", {}).get("title", "Active Goal")
        return {
            "action": "CONTINUE",
            "title": f"Continue {goal_title} Session",
            "reason": "You're progressing smoothly. Proceed to the next core module.",
            "topic": goal_title,
            "estimated_minutes": 30
        }
