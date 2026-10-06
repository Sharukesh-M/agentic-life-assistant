"""
services/learning/roadmap_service.py — Dynamic Goal Roadmap Generation & Lifecycle Management

Implements complete dynamic roadmap generation according to JARVIS-X specifications.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class RoadmapService:
    """Manages creation, adaptation, expansion, and storage of goal roadmaps."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def generate_roadmap(self, user_context: Dict[str, Any], goal_title: str) -> Dict[str, Any]:
        """Generates a complete personalized roadmap for a goal."""
        goal_info = user_context.get("current_goal", {})
        goal_id = goal_info.get("id", f"goal-{int(datetime.now().timestamp())}")
        target_outcome = goal_info.get("target_outcome", f"Achieve outcome for {goal_title}")

        prompt = f"""
Generate a complete, structured learning roadmap for the following user goal:
Goal Title: "{goal_title}"
Target Outcome: "{target_outcome}"
User Level: "{user_context.get('current_skill_level', {}).get('overall', 'beginner')}"
Daily Minutes: {user_context.get('availability', {}).get('daily_minutes', 45)}
Role/Profession: "{user_context.get('identity', {}).get('role', 'Learner')}"

Return JSON matching this exact structure:
{{
  "title": "{goal_title}",
  "description": "Comprehensive roadmap to reach target outcome.",
  "target_outcome": "{target_outcome}",
  "estimated_total_hours": 40,
  "milestones": [
    {{
      "milestone_id": "m1",
      "title": "Milestone 1: Foundations",
      "description": "Core concepts and setup",
      "order": 1,
      "priority": "high",
      "estimated_hours": 10,
      "deadline": "1 week",
      "status": "pending",
      "progress": 0,
      "modules": [
        {{
          "module_id": "mod-1",
          "title": "Module 1: Core Fundamentals",
          "description": "Basic building blocks",
          "order": 1,
          "estimated_minutes": 120,
          "prerequisites": [],
          "status": "pending",
          "topics": [
            {{
              "topic_id": "top-1",
              "title": "Syntax & Basic Structures",
              "description": "Introduction and basic usage",
              "difficulty": "beginner",
              "estimated_minutes": 45,
              "status": "pending",
              "dependencies": []
            }}
          ]
        }}
      ]
    }}
  ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or not res.get("milestones"):
            res = self._build_fallback_roadmap(goal_id, goal_title, target_outcome, user_context)

        # Ensure IDs and dates
        rid = f"rdm-{int(datetime.now().timestamp())}"
        roadmap_data = {
            "roadmap_id": rid,
            "goal_id": goal_id,
            "title": res.get("title", goal_title),
            "description": res.get("description", f"Roadmap for {goal_title}"),
            "target_outcome": res.get("target_outcome", target_outcome),
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "target_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "estimated_total_hours": res.get("estimated_total_hours", 30),
            "status": "active",
            "progress": 0,
            "milestones": res.get("milestones", []),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        self.store.save_roadmap(roadmap_data)
        return roadmap_data

    def _build_fallback_roadmap(self, goal_id: str, goal_title: str, target_outcome: str, user_ctx: Dict[str, Any]) -> Dict[str, Any]:
        level = user_ctx.get("current_skill_level", {}).get("overall", "beginner")
        return {
            "title": f"Personalized Roadmap: {goal_title}",
            "description": f"Targeted milestone roadmap to reach {target_outcome}.",
            "target_outcome": target_outcome,
            "estimated_total_hours": 35,
            "milestones": [
                {
                    "milestone_id": "m1",
                    "title": "Phase 1: Foundations & Core Capabilities",
                    "description": "Establish key principles and fundamental skills.",
                    "order": 1,
                    "priority": "high",
                    "estimated_hours": 10,
                    "deadline": "1 week",
                    "status": "in_progress",
                    "progress": 0,
                    "modules": [
                        {
                            "module_id": "mod-101",
                            "title": "Fundamental Concepts & Setup",
                            "description": "Core concepts and initial hands-on exercise.",
                            "order": 1,
                            "estimated_minutes": 120,
                            "prerequisites": [],
                            "status": "in_progress",
                            "topics": [
                                {
                                    "topic_id": "top-101",
                                    "title": f"Introduction to {goal_title}",
                                    "description": "Key concepts, terminology, and setup.",
                                    "difficulty": level,
                                    "estimated_minutes": 45,
                                    "status": "in_progress",
                                    "dependencies": []
                                },
                                {
                                    "topic_id": "top-102",
                                    "title": "Practical Worked Example & Guided Practice",
                                    "description": "Step-by-step implementation and basic exercises.",
                                    "difficulty": level,
                                    "estimated_minutes": 45,
                                    "status": "pending",
                                    "dependencies": ["top-101"]
                                }
                            ]
                        }
                    ]
                },
                {
                    "milestone_id": "m2",
                    "title": "Phase 2: Applied Problem Solving & Projects",
                    "description": "Build real-world projects and master common patterns.",
                    "order": 2,
                    "priority": "medium",
                    "estimated_hours": 15,
                    "deadline": "2 weeks",
                    "status": "pending",
                    "progress": 0,
                    "modules": [
                        {
                            "module_id": "mod-102",
                            "title": "Applied Project Module",
                            "description": "Practical application and problem-solving.",
                            "order": 2,
                            "estimated_minutes": 180,
                            "prerequisites": ["mod-101"],
                            "status": "pending",
                            "topics": [
                                {
                                    "topic_id": "top-103",
                                    "title": "Common Patterns & Architectural Best Practices",
                                    "description": "Learn patterns and optimizations.",
                                    "difficulty": "intermediate",
                                    "estimated_minutes": 60,
                                    "status": "pending",
                                    "dependencies": ["top-102"]
                                }
                            ]
                        }
                    ]
                },
                {
                    "milestone_id": "m3",
                    "title": "Phase 3: Goal Mastery & Interview/Execution Prep",
                    "description": "Targeted revision, timed mock assessments, and final deployment.",
                    "order": 3,
                    "priority": "high",
                    "estimated_hours": 10,
                    "deadline": "3 weeks",
                    "status": "pending",
                    "progress": 0,
                    "modules": [
                        {
                            "module_id": "mod-103",
                            "title": "Final Assessment & Portfolio",
                            "description": "Comprehensive evaluation and final outcome completion.",
                            "order": 3,
                            "estimated_minutes": 120,
                            "prerequisites": ["mod-102"],
                            "status": "pending",
                            "topics": [
                                {
                                    "topic_id": "top-104",
                                    "title": "Final Assessment & Benchmark Check",
                                    "description": "Evaluate end-to-end outcome readiness.",
                                    "difficulty": "advanced",
                                    "estimated_minutes": 60,
                                    "status": "pending",
                                    "dependencies": ["top-103"]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
