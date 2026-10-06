"""
services/learning/lesson_service.py — Interactive Lesson & Content Block Generation Service

Generates structured content blocks (concept cards, diagrams, flowcharts, worked examples, code blocks, practice)
for any topic using the Gemini Learning API.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class LessonService:
    """Generates structured, visual, interactive lessons for JARVIS-X."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def generate_lesson(
        self,
        user_context: Dict[str, Any],
        topic_title: str,
        goal_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates a complete interactive lesson block for a topic."""
        goal_str = goal_title or user_context.get("current_goal", {}).get("title", "General Skill")
        level = user_context.get("current_skill_level", {}).get("overall", "beginner")
        available_time = user_context.get("availability", {}).get("daily_minutes", 45)

        prompt = f"""
Generate an interactive, structured lesson for topic: "{topic_title}"
Target Goal: "{goal_str}"
User Level: "{level}"
Available Time: {available_time} minutes

Return JSON conforming to this schema:
{{
  "lesson_id": "lsn-123",
  "topic_title": "{topic_title}",
  "goal_title": "{goal_str}",
  "objective": "Clear learning objective",
  "estimated_minutes": {available_time},
  "blocks": [
    {{
      "type": "CONCEPT_CARD",
      "title": "{topic_title} Core Concept",
      "content": "Explanation",
      "key_points": ["Point 1", "Point 2"]
    }},
    {{
      "type": "FLOWCHART",
      "title": "{topic_title} Execution Flow",
      "nodes": [{{"id": "1", "label": "Start"}}, {{"id": "2", "label": "Process"}}],
      "edges": [{{"from": "1", "to": "2"}}]
    }},
    {{
      "type": "EXAMPLE",
      "title": "Worked Example",
      "content": "Step by step code or solution"
    }},
    {{
      "type": "PRACTICE",
      "title": "Practice Question",
      "difficulty": "{level}",
      "questions": [
        {{
          "id": 1,
          "question": "Sample question?",
          "options": ["Opt A", "Opt B", "Opt C", "Opt D"],
          "correct": 0,
          "explanation": "Why Opt A is correct."
        }}
      ]
    }}
  ],
  "image_generation_requests": [
    {{
      "purpose": "Explain core structure visually",
      "prompt": "Clean technical educational illustration of {topic_title}",
      "aspect_ratio": "16:9"
    }}
  ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or not res.get("blocks"):
            res = self._build_fallback_lesson(topic_title, goal_str, level, available_time)

        lesson_id = res.get("lesson_id") or f"lsn-{int(datetime.now().timestamp())}"
        lesson_data = {
            "lesson_id": lesson_id,
            "topic_title": topic_title,
            "goal_title": goal_str,
            "objective": res.get("objective", f"Master {topic_title} for {goal_str}"),
            "estimated_minutes": res.get("estimated_minutes", available_time),
            "blocks": res.get("blocks", []),
            "image_generation_requests": res.get("image_generation_requests", []),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.store.save_lesson(lesson_data)
        return lesson_data

    def _build_fallback_lesson(
        self,
        topic_title: str,
        goal_str: str,
        level: str,
        available_time: int,
    ) -> Dict[str, Any]:
        return {
            "lesson_id": f"lsn-{int(datetime.now().timestamp())}",
            "topic_title": topic_title,
            "goal_title": goal_str,
            "objective": f"Understand core principles of {topic_title} and apply them to {goal_str}.",
            "estimated_minutes": available_time,
            "blocks": [
                {
                    "type": "CONCEPT_CARD",
                    "title": f"Understanding {topic_title}",
                    "content": f"{topic_title} provides essential capabilities for {goal_str}. Master core syntax, operational logic, and common edge cases.",
                    "key_points": [
                        f"Core principles of {topic_title}",
                        "Practical implementation techniques",
                        "Optimization and common pitfalls"
                    ]
                },
                {
                    "type": "FLOWCHART",
                    "title": f"{topic_title} Process Flow",
                    "nodes": [
                        {"id": "1", "label": "Initialize Inputs"},
                        {"id": "2", "label": f"Execute {topic_title} Logic"},
                        {"id": "3", "label": "Validate Output"}
                    ],
                    "edges": [
                        {"from": "1", "to": "2"},
                        {"from": "2", "to": "3"}
                    ]
                },
                {
                    "type": "EXAMPLE",
                    "title": f"Worked Example: {topic_title}",
                    "content": f"Step 1: Set up problem environment.\nStep 2: Apply {topic_title} logic.\nStep 3: Verify result."
                },
                {
                    "type": "PRACTICE",
                    "title": f"Quick Practice: {topic_title}",
                    "difficulty": level,
                    "questions": [
                        {
                            "id": 1,
                            "question": f"What is the key objective of applying {topic_title}?",
                            "options": [
                                "Improves solution efficiency and structure",
                                "Increases computation overhead",
                                "Bypasses error checking",
                                "None of the above"
                            ],
                            "correct": 0,
                            "explanation": f"Applying {topic_title} structures the logic cleanly and reduces complexity."
                        }
                    ]
                }
            ],
            "image_generation_requests": [
                {
                    "purpose": f"Visual summary of {topic_title}",
                    "prompt": f"Clean technical educational illustration explaining {topic_title}",
                    "aspect_ratio": "16:9"
                }
            ]
        }
