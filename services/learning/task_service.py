"""
services/learning/task_service.py — Goal-Aware Task Generation & Adaptive Rescheduling Service

Generates learning tasks linked to roadmaps, milestones, and topics, and handles task adaptation.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from memory.task_store import Task, TaskStatus, get_task_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class LearningTaskService:
    """Manages learning task generation and adaptive rescheduling."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.task_store = get_task_store()

    def generate_daily_tasks(
        self,
        user_context: Dict[str, Any],
        roadmap: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generates realistic daily tasks aligned with active roadmap and time availability."""
        goal_info = user_context.get("current_goal", {})
        goal_id = goal_info.get("id", "")
        goal_title = goal_info.get("title", "Active Goal")
        available_minutes = user_context.get("availability", {}).get("daily_minutes", 45)

        roadmap_id = roadmap.get("roadmap_id", "") if roadmap else ""
        milestones = roadmap.get("milestones", []) if roadmap else []

        milestone_id = milestones[0].get("milestone_id", "") if milestones else ""
        topic_title = "Core Practice"
        if milestones and milestones[0].get("modules"):
            mod = milestones[0]["modules"][0]
            if mod.get("topics"):
                topic_title = mod["topics"][0].get("title", "Core Practice")

        prompt = f"""
Generate 2-3 specific learning tasks for today:
Goal: "{goal_title}"
Topic: "{topic_title}"
Available Total Minutes: {available_minutes}

Return JSON array of tasks:
[
  {{
    "title": "Study {topic_title}",
    "description": "Understand core concepts and review worked examples",
    "duration_minutes": 25,
    "priority": 1
  }},
  {{
    "title": "Practice {topic_title} Exercises",
    "description": "Solve practice questions and test understanding",
    "duration_minutes": 20,
    "priority": 1
  }}
]
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        raw_tasks = res.get("tasks", []) if isinstance(res, dict) and "tasks" in res else (res if isinstance(res, list) else [])
        if not raw_tasks or res.get("status") == "LEARNING_GENERATION_FAILED":
            raw_tasks = [
                {
                    "title": f"Study {topic_title}",
                    "description": f"Learn key principles and examples for {topic_title}.",
                    "duration_minutes": max(20, available_minutes // 2),
                    "priority": 1
                },
                {
                    "title": f"Complete {topic_title} Practice & Quiz",
                    "description": f"Solve practice questions to reinforce understanding.",
                    "duration_minutes": max(15, available_minutes // 2),
                    "priority": 1
                }
            ]

        created_tasks = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            t = Task(
                title=item.get("title", f"Study {topic_title}"),
                description=item.get("description", ""),
                duration_minutes=item.get("duration_minutes", 30),
                priority=item.get("priority", 1),
                goal_id=goal_id,
                goal_subject=goal_title,
                scheduled_date=datetime.now().strftime("%Y-%m-%d"),
            )
            self.task_store.add(t)
            created_tasks.append(t.to_dict())

        return created_tasks

    def adapt_missed_task(self, task_id: str, reason: str = "time constraint") -> Dict[str, Any]:
        """Adapts a missed/postponed learning task using: RESUME, SPLIT, SHORTEN, RESCHEDULE, DEFER, REPRIORITIZE."""
        task = self.task_store.get(task_id)
        if not task:
            return {"action": "RESCHEDULE", "reason": "Task not found, rescheduled to tomorrow"}

        prompt = f"""
A learning task was missed:
Title: "{task.title}"
Duration: {task.duration_minutes} minutes
Reason: "{reason}"

Select the best adaptation action from: [RESUME, SPLIT, SHORTEN, RESCHEDULE, DEFER, REPRIORITIZE]
Return JSON:
{{
  "action": "SHORTEN",
  "explanation": "Reduce session duration to 15 mins micro-learning",
  "new_duration_minutes": 15,
  "rescheduled_date": "{datetime.now().strftime('%Y-%m-%d')}"
}}
"""
        res = self.client.generate_json(prompt)
        action = res.get("action", "RESCHEDULE")

        if action == "SHORTEN":
            task.duration_minutes = res.get("new_duration_minutes", max(15, task.duration_minutes // 2))
            task.scheduled_date = datetime.now().strftime("%Y-%m-%d")
        elif action == "SPLIT":
            task.duration_minutes = max(15, task.duration_minutes // 2)
            # Create second split half
            t2 = Task(
                title=f"{task.title} (Part 2)",
                description=task.description,
                duration_minutes=task.duration_minutes,
                goal_id=task.goal_id,
                goal_subject=task.goal_subject,
                scheduled_date=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            )
            self.task_store.add(t2)
        else:
            task.scheduled_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        task.skip_count += 1
        task.skip_reasons.append(reason)
        self.task_store.update(task)

        return {
            "task_id": task_id,
            "title": task.title,
            "action": action,
            "explanation": res.get("explanation", f"Task adapted via {action}"),
            "updated_task": task.to_dict()
        }
