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

    def generate_learning_window_content(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generates dynamic recommended modules, video resources, and web documentation based on active user goals and tasks."""
        goal_info = user_context.get("current_goal") or {}
        if not goal_info:
            return {"modules": [], "videos": [], "web": []}

        goal_title = goal_info.get("subject") or goal_info.get("title") or ""
        if not goal_title:
            return {"modules": [], "videos": [], "web": []}

        level = user_context.get("user_level", "beginner")
        pending_tasks = user_context.get("pending_tasks", [])

        prompt = f"""You are the JARVIS-X Learning Intelligence Engine.

Generate a personalized set of recommended learning modules, video resources, and web resources for:
Target Goal: "{goal_title}"
Skill Level: "{level}"
Pending Tasks: {json.dumps(pending_tasks)}

Return STRICT JSON matching this schema:
{{
    "modules": [
        "Module 1: Title for Goal",
        "Module 2: Title for Goal",
        "Module 3: Title for Goal"
    ],
    "videos": [
        {{"title": "Video Tutorial Title", "url": "https://www.youtube.com/watch?v=aircAruvnKk"}},
        {{"title": "Deep Dive Lecture Title", "url": "https://www.youtube.com/watch?v=SZorAJ4I-sA"}}
    ],
    "web": [
        {{"title": "Official Documentation / Course Title", "url": "https://pytorch.org/docs/stable/index.html"}},
        {{"title": "Reference Guide Title", "url": "https://huggingface.co/learn/nlp-course/chapter1/1"}}
    ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")
        if not isinstance(res, dict) or "modules" not in res or not res.get("modules"):
            plan_ms = (goal_info.get("plan") or {}).get("milestones") or []
            fallback_mods = []
            for idx, ms in enumerate(plan_ms, 1):
                m_t = ms.get("title") if isinstance(ms, dict) else str(ms)
                fallback_mods.append(f"Module {idx}: {m_t}")

            if not fallback_mods:
                fallback_mods = [
                    f"Module 1: {goal_title} Foundations & Core Principles",
                    f"Module 2: Advanced {goal_title} Architecture & Concepts",
                    f"Module 3: Hands-On {goal_title} Capstone & Execution"
                ]

            q_enc = goal_title.replace(" ", "+")
            fallback_vids = [
                {"title": f"{goal_title} Full Tutorial & Strategy Guide", "url": f"https://www.youtube.com/results?search_query={q_enc}+tutorial"},
                {"title": f"{goal_title} Deep Dive & Practical Mastery", "url": f"https://www.youtube.com/results?search_query={q_enc}+masterclass"}
            ]
            fallback_web = [
                {"title": f"Official Reference & Documentation for {goal_title}", "url": f"https://www.google.com/search?q={q_enc}+documentation"},
                {"title": f"{goal_title} Roadmap & Best Practices", "url": f"https://www.google.com/search?q={q_enc}+guide"}
            ]

            res = {
                "modules": fallback_mods,
                "videos": fallback_vids,
                "web": fallback_web
            }
        return res

