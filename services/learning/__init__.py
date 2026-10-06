"""
services/learning — Unified JARVIS-X Learning Intelligence System

Centralizes all learning services behind one Gemini Learning API and persistence pipeline:
- GeminiLearningClient
- RoadmapService
- LessonService
- LearningTaskService
- QuizService
- CodingService
- AssessmentService
- LearningProgressService
- LearningRecommendationService
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.learning.assessment_service import AssessmentService
from services.learning.coding_service import CodingService
from services.learning.gemini_learning_client import GeminiLearningClient, get_gemini_learning_client
from services.learning.lesson_service import LessonService
from services.learning.progress_service import LearningProgressService
from services.learning.quiz_service import QuizService
from services.learning.recommendation_service import LearningRecommendationService
from services.learning.roadmap_service import RoadmapService
from services.learning.task_service import LearningTaskService


class LearningIntelligenceService:
    """Unified Facade for JARVIS-X Learning Intelligence Engine."""

    def __init__(self):
        self.gemini_client = get_gemini_learning_client()
        self.roadmap_service = RoadmapService()
        self.lesson_service = LessonService()
        self.task_service = LearningTaskService()
        self.quiz_service = QuizService()
        self.coding_service = CodingService()
        self.assessment_service = AssessmentService()
        self.progress_service = LearningProgressService()
        self.recommendation_service = LearningRecommendationService()

    def process_learning_request(self, request_type: str, user_context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Routes learning requests to appropriate intelligence service."""
        request_type = request_type.lower().strip()

        if request_type in ("roadmap", "generate_roadmap"):
            goal_title = kwargs.get("goal_title", kwargs.get("subject", "Software Developer"))
            return self.roadmap_service.generate_roadmap(user_context, goal_title)

        elif request_type in ("lesson", "generate_lesson", "content"):
            topic_title = kwargs.get("topic_title", kwargs.get("subject", "Core Principles"))
            goal_title = kwargs.get("goal_title", None)
            return self.lesson_service.generate_lesson(user_context, topic_title, goal_title)

        elif request_type in ("tasks", "daily_tasks"):
            roadmap = kwargs.get("roadmap", None)
            return {"tasks": self.task_service.generate_daily_tasks(user_context, roadmap)}

        elif request_type in ("quiz", "generate_quiz"):
            topic_title = kwargs.get("topic_title", kwargs.get("subject", "General Practice"))
            num_q = kwargs.get("num_questions", 3)
            return self.quiz_service.generate_quiz(user_context, topic_title, num_q)

        elif request_type in ("coding", "code_challenge"):
            topic_title = kwargs.get("topic_title", kwargs.get("subject", "DSA Arrays"))
            lang = kwargs.get("language", "python")
            return self.coding_service.generate_challenge(user_context, topic_title, lang)

        elif request_type in ("progress", "summary"):
            return self.progress_service.get_progress_summary()

        elif request_type in ("next_step", "recommendation"):
            return self.recommendation_service.get_next_step(user_context)

        # Default fallback: lesson generation
        topic_title = kwargs.get("subject", "General Learning Session")
        return self.lesson_service.generate_lesson(user_context, topic_title)


_intelligence_instance: Optional[LearningIntelligenceService] = None


def get_learning_intelligence_service() -> LearningIntelligenceService:
    global _intelligence_instance
    if _intelligence_instance is None:
        _intelligence_instance = LearningIntelligenceService()
    return _intelligence_instance


__all__ = [
    "GeminiLearningClient",
    "get_gemini_learning_client",
    "RoadmapService",
    "LessonService",
    "LearningTaskService",
    "QuizService",
    "CodingService",
    "AssessmentService",
    "LearningProgressService",
    "LearningRecommendationService",
    "LearningIntelligenceService",
    "get_learning_intelligence_service",
]
