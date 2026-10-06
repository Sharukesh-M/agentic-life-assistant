"""
services/learning/assessment_service.py — Assessment Service for JARVIS-X Learning Engine

Manages milestone benchmarks, skill gap evaluations, and mock test scoring.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class AssessmentService:
    """Manages skill gap assessments and milestone benchmarks."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def generate_skill_gap_assessment(
        self,
        user_context: Dict[str, Any],
        goal_title: str,
    ) -> Dict[str, Any]:
        """Performs a skill gap evaluation and returns prioritized learning focus areas."""
        level = user_context.get("current_skill_level", {}).get("overall", "beginner")

        prompt = f"""
Perform a skill gap assessment for goal: "{goal_title}"
User Demonstrated Level: "{level}"
Completed Topics: {user_context.get('progress', {}).get('completed_topics', [])}
Weak Topics: {user_context.get('progress', {}).get('weak_topics', [])}

Return JSON:
{{
  "assessment_id": "assess-1",
  "goal_title": "{goal_title}",
  "readiness_score_percent": 65,
  "top_gaps": ["Data Structures", "API Integration"],
  "strengths": ["Basic Syntax", "Control Flow"],
  "actionable_recommendation": "Focus next 3 sessions on array and hashing problems."
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or "readiness_score_percent" not in res:
            res = {
                "assessment_id": f"assess-{int(datetime.now().timestamp())}",
                "goal_title": goal_title,
                "readiness_score_percent": 70,
                "top_gaps": user_context.get('progress', {}).get('weak_topics', ["Applied Algorithms"]),
                "strengths": user_context.get('progress', {}).get('completed_topics', ["Core Concepts"]),
                "actionable_recommendation": f"Continue with structured practice on {goal_title} fundamentals."
            }

        return res
