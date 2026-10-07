"""
services/goal_intelligence_service.py — Universal Goal Intelligence Engine for JARVIS-X

Implements goal analysis, mode determination (Career, Business, Education, Project, Fitness, Travel, etc.),
universal Gemini intelligence system prompt integration, dynamic item click routing, and multi-goal orchestration.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from memory.task_store import Task, get_task_store
from services.learning.gemini_learning_client import get_gemini_learning_client


UNIVERSAL_GOAL_SYSTEM_PROMPT = """You are the Goal Intelligence Engine of JARVIS-X.

JARVIS-X is a proactive personal AI assistant that helps users achieve arbitrary goals.

You must NEVER assume that the user's goal is about education, learning, coding, career, or any particular domain.

First understand the user's desired outcome.
Then determine the appropriate strategy, milestones, tasks, actions, knowledge requirements, schedule requirements, resources, and monitoring requirements.

Your job is to help transform:
USER INTENTION → CLEAR OUTCOME → GOAL PLAN → MILESTONES → ACTIONS → EXECUTION → PROGRESS → ADAPTATION → SUCCESS

---------------------------------------------------------------
USER CONTEXT
---------------------------------------------------------------
USER_PROFILE:
{USER_PROFILE}

ACTIVE_GOALS:
{ACTIVE_GOALS}

CURRENT_GOAL:
{CURRENT_GOAL}

GOAL_CATEGORY:
{GOAL_CATEGORY}

DEADLINE:
{DEADLINE}

USER_SCHEDULE:
{USER_SCHEDULE}

AVAILABLE_TIME:
{AVAILABLE_TIME}

PREFERENCES:
{PREFERENCES}

CURRENT_PROGRESS:
{CURRENT_PROGRESS}

COMPLETED_TASKS:
{COMPLETED_TASKS}

PENDING_TASKS:
{PENDING_TASKS}

PREVIOUS_ATTEMPTS:
{PREVIOUS_ATTEMPTS}

CONSTRAINTS:
{CONSTRAINTS}

USER_REQUEST:
{USER_REQUEST}

---------------------------------------------------------------
ADAPTIVE DOMAIN BEHAVIOR
---------------------------------------------------------------
Select appropriate goal modes from:
LEARNING_MODE, PROJECT_MODE, CAREER_MODE, BUSINESS_MODE, FITNESS_MODE, FINANCE_MODE, TRAVEL_MODE, RESEARCH_MODE, PRODUCTIVITY_MODE, PERSONAL_DEVELOPMENT_MODE, EXECUTION_MODE, CUSTOM_MODE

Determine whether LEARNING is actually required.
If YES: generate concepts, explanations, worked examples, practice, quizzes.
If NO: do NOT generate unnecessary educational content. Focus on real-world actions, checklists, research, execution steps, or itineraries.

---------------------------------------------------------------
OUTPUT FORMAT
---------------------------------------------------------------
Return STRICT JSON.

Schema:
{{
    "type": "GOAL_INTELLIGENCE_RESPONSE",
    "goal": {{
        "goal_id": "...",
        "title": "...",
        "category": "...",
        "target_outcome": "...",
        "priority": "HIGH",
        "deadline": "..."
    }},
    "goal_modes": ["CAREER_MODE", "PROJECT_MODE"],
    "analysis": {{
        "desired_outcome": "...",
        "current_state": "...",
        "gap": "...",
        "learning_required": false
    }},
    "milestones": [
        {{
            "milestone_id": "m1",
            "title": "...",
            "status": "pending",
            "description": "..."
        }}
    ],
    "tasks": [
        {{
            "task_id": "t1",
            "title": "...",
            "description": "...",
            "milestone_id": "m1",
            "priority": 1,
            "estimated_minutes": 30,
            "scheduled_date": "YYYY-MM-DD"
        }}
    ],
    "content": [
        {{
            "type": "CHECKLIST",
            "title": "...",
            "items": ["..."]
        }},
        {{
            "type": "PROCESS_FLOW",
            "title": "...",
            "nodes": [{{"id": "1", "label": "Start"}}],
            "edges": [{{"from": "1", "to": "2"}}]
        }}
    ],
    "visualizations": [],
    "recommendations": [
        {{
            "title": "...",
            "action": "..."
        }}
    ],
    "next_action": {{
        "type": "EXECUTE",
        "title": "...",
        "reason": "..."
    }},
    "progress_update": {{
        "percentage": 0,
        "summary": "..."
    }}
}}
"""


class UniversalGoalIntelligenceService:
    """Central Intelligence Engine for arbitrary user goals in JARVIS-X."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()
        self.task_store = get_task_store()
        self._goals_path = Path(__file__).resolve().parent.parent / "memory" / "goals.json"

    # --- Data Loaders ---
    def load_goals(self) -> List[Dict[str, Any]]:
        if self._goals_path.exists():
            try:
                data = json.loads(self._goals_path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                pass
        return []

    def save_goals(self, goals: List[Dict[str, Any]]) -> None:
        try:
            self._goals_path.parent.mkdir(parents=True, exist_ok=True)
            self._goals_path.write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            print(f"[GoalIntelligenceService] Save goals error: {exc}")

    def get_user_profile(self) -> Dict[str, Any]:
        p_path = Path(__file__).resolve().parent.parent / "memory" / "profile.json"
        if p_path.exists():
            try:
                return json.loads(p_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"name": "JARVIS User", "role": "User"}

    # --- Core Goal Analysis & Intelligence ---
    def analyze_goal(self, goal_input: str, category: str = "custom") -> Dict[str, Any]:
        """Analyzes a new or existing goal using the Universal Gemini Intelligence Engine."""
        print(f"\n[GOAL_INTELLIGENCE_ANALYSIS] input='{goal_input}' category='{category}'")

        goals = self.load_goals()
        user_prof = self.get_user_profile()
        today_tasks = [t.to_dict() for t in self.task_store.today()]

        prompt = UNIVERSAL_GOAL_SYSTEM_PROMPT.format(
            USER_PROFILE=json.dumps(user_prof),
            ACTIVE_GOALS=json.dumps(goals),
            CURRENT_GOAL=goal_input,
            GOAL_CATEGORY=category,
            DEADLINE="Flexible / Target 90 Days",
            USER_SCHEDULE="45-60 mins daily available",
            AVAILABLE_TIME="45 minutes",
            PREFERENCES="Action-oriented, practical milestones, high clarity",
            CURRENT_PROGRESS="New / Active Goal Initialization",
            COMPLETED_TASKS=json.dumps([t for t in today_tasks if t.get("status") == "completed"]),
            PENDING_TASKS=json.dumps([t for t in today_tasks if t.get("status") == "pending"]),
            PREVIOUS_ATTEMPTS="None",
            CONSTRAINTS="None specified",
            USER_REQUEST=f"Decompose and create complete action intelligence for goal: {goal_input}",
        )

        res = self.client.generate_json(prompt, system_instruction="You are the Goal Intelligence Engine of JARVIS-X.")

        validated = self._validate_goal_response(res, goal_input, category)
        
        # Persist goal structure to goals.json
        self._persist_analyzed_goal(validated)

        # Seed generated tasks into TaskStore
        created_task_ids = []
        for t_item in validated.get("tasks", []):
            if isinstance(t_item, dict):
                t = Task(
                    title=t_item.get("title", f"Action item for {goal_input}"),
                    description=t_item.get("description", ""),
                    duration_minutes=t_item.get("estimated_minutes", 30),
                    priority=t_item.get("priority", 1),
                    goal_id=validated["goal"]["goal_id"],
                    goal_subject=validated["goal"]["title"],
                    scheduled_date=t_item.get("scheduled_date", datetime.now().strftime("%Y-%m-%d")),
                )
                self.task_store.add(t)
                created_task_ids.append(t.id)

        validated["created_task_ids"] = created_task_ids
        print(f"[GOAL_INTELLIGENCE_COMPLETE] goal_id={validated['goal']['goal_id']} tasks_seeded={len(created_task_ids)}\n")
        return validated

    def handle_item_click(self, item_id: str, item_title: str, item_type: str = "auto") -> Dict[str, Any]:
        """
        Dynamic Item Click Router:
        Determines item category & type, loads context, and generates the target experience.
        """
        print(f"\n[GOAL_ITEM_CLICK] item_id={item_id} title='{item_title}' type={item_type}")

        title_lower = item_title.lower()

        # Classify experience mode
        if any(w in title_lower for w in ["learn", "python", "dsa", "course", "study", "concept", "algorithm"]):
            experience_type = "learning_session"
            from services.learning.interactive_session_service import get_interactive_session_service
            session = get_interactive_session_service().handle_module_click(item_title)
            return {"experience_type": "learning", "data": session}

        elif any(w in title_lower for w in ["code", "build", "app", "website", "deploy", "repo", "api"]):
            experience_type = "project_workspace"
            return {
                "experience_type": "project",
                "title": item_title,
                "starter_code": f"# {item_title} Project Workspace\ndef main():\n    print('Executing {item_title}')\n\nif __name__ == '__main__':\n    main()",
                "checklists": ["Setup Repository", "Implement Core Logic", "Run Tests", "Deploy Build"]
            }

        elif any(w in title_lower for w in ["business", "supplier", "market", "pricing", "customer", "startup"]):
            experience_type = "business_workspace"
            return {
                "experience_type": "business",
                "title": item_title,
                "checklists": ["Market Analysis", "Competitor Pricing Comparison", "Supplier Outreach", "Financial Projection"],
                "content_blocks": [
                    {
                        "type": "CHECKLIST",
                        "title": f"Business Action Checklist: {item_title}",
                        "items": ["Identify top 5 competitors", "Record pricing matrix", "Draft vendor inquiry email"]
                    }
                ]
            }

        elif any(w in title_lower for w in ["run", "workout", "gym", "fitness", "muscle", "diet", "10k"]):
            experience_type = "fitness_workspace"
            return {
                "experience_type": "fitness",
                "title": item_title,
                "workout_plan": ["Warm-up (5m)", "Main Training Session (30m)", "Cool-down & Stretch (10m)"],
                "checklists": ["Hydration Check", "Pre-workout Snack", "Log Distance/Reps"]
            }

        elif any(w in title_lower for w in ["flight", "hotel", "trip", "travel", "itinerary", "booking"]):
            experience_type = "travel_workspace"
            return {
                "experience_type": "travel",
                "title": item_title,
                "itinerary": [
                    {"time": "Day 1", "activity": "Arrival & Hotel Check-in"},
                    {"time": "Day 2", "activity": "Sightseeing & Local Excursions"}
                ],
                "checklists": ["Passport / Visa Check", "Pack Travel Gear", "Confirm Reservations"]
            }

        else:
            experience_type = "execution_workspace"
            return {
                "experience_type": "execution",
                "title": item_title,
                "checklists": [f"Review requirements for {item_title}", f"Execute core task steps", "Log completion status"],
                "content_blocks": [
                    {
                        "type": "EXPLANATION",
                        "title": f"Action Overview: {item_title}",
                        "content": f"Perform the required action steps to advance this goal milestone."
                    }
                ]
            }

    # --- Validation & Fallbacks ---
    def _validate_goal_response(self, raw: Dict[str, Any], goal_title: str, category: str) -> Dict[str, Any]:
        if not isinstance(raw, dict) or raw.get("type") != "GOAL_INTELLIGENCE_RESPONSE":
            raw = {}

        g_info = raw.get("goal") or {}
        g_id = g_info.get("goal_id") or f"goal-{uuid.uuid4().hex[:8]}"
        
        gt_lower = goal_title.lower()
        if not raw.get("milestones"):
            if any(w in gt_lower for w in ["ai", "machine learning", "developer", "software", "engineer", "python", "code"]):
                milestones = [
                    {"milestone_id": "m1", "title": "Python & Data Structures Mastery", "status": "in_progress", "description": f"Foundational programming and algorithmic data structures for {goal_title}"},
                    {"milestone_id": "m2", "title": "Mathematics & Core Machine Learning", "status": "pending", "description": f"Linear algebra, calculus, probability and Scikit-Learn algorithms for {goal_title}"},
                    {"milestone_id": "m3", "title": "Deep Learning & Neural Networks", "status": "pending", "description": f"PyTorch, neural network architectures, and deep learning for {goal_title}"},
                    {"milestone_id": "m4", "title": "Advanced AI Systems & Capstones", "status": "pending", "description": f"Transformers, LLM fine-tuning, RAG, and production capstone projects"},
                    {"milestone_id": "m5", "title": "Interview Preparation & Portfolio Optimization", "status": "pending", "description": f"Technical coding practice, system design, and resume optimization"}
                ]
            elif any(w in gt_lower for w in ["gate", "exam", "test", "certification"]):
                milestones = [
                    {"milestone_id": "m1", "title": "Syllabus Breakdown & High-Yield Math", "status": "in_progress", "description": f"Linear algebra, calculus, and probability syllabus for {goal_title}"},
                    {"milestone_id": "m2", "title": "Core Technical Subject Mastery", "status": "pending", "description": f"Algorithms, machine learning, and core CS syllabus"},
                    {"milestone_id": "m3", "title": "Previous Year Questions & Mock Exams", "status": "pending", "description": f"Solving PYQs and full-length simulated GATE exams"}
                ]
            else:
                milestones = [
                    {"milestone_id": "m1", "title": f"{goal_title} Foundations & Setup", "status": "in_progress", "description": f"Initial research and foundation phase for {goal_title}"},
                    {"milestone_id": "m2", "title": f"Core Execution & Milestone Delivery", "status": "pending", "description": f"Primary implementation tasks for {goal_title}"},
                    {"milestone_id": "m3", "title": f"Review, Optimization & Completion", "status": "pending", "description": f"Final verification and launch of {goal_title}"}
                ]

        if not raw.get("tasks"):
            if any(w in gt_lower for w in ["ai", "machine learning", "developer", "software", "engineer", "python", "code"]):
                tasks = [
                    {
                        "task_id": "t1",
                        "title": f"Master Python Fundamentals: Variables, Loops & Functions",
                        "description": f"Core programming building block for {goal_title}.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 45,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    },
                    {
                        "task_id": "t2",
                        "title": f"Complete 5 practice problems for Data Structures (Lists, Dicts, Sets)",
                        "description": f"Algorithmic practice for {goal_title} technical assessments.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 45,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]
            elif any(w in gt_lower for w in ["gate", "exam", "test"]):
                tasks = [
                    {
                        "task_id": "t1",
                        "title": f"Review Official {goal_title} Syllabus & Weightage Breakdown",
                        "description": f"Identify top high-weightage topics for {goal_title}.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 30,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    },
                    {
                        "task_id": "t2",
                        "title": f"Solve 10 Practice Questions for Linear Algebra & Probability",
                        "description": f"Exam practice session for {goal_title}.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 45,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]
            else:
                tasks = [
                    {
                        "task_id": "t1",
                        "title": f"Define Action Plan & Objectives for {goal_title}",
                        "description": f"Initial setup task for {goal_title}.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 30,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    },
                    {
                        "task_id": "t2",
                        "title": f"Execute Core Step 1 for {goal_title}",
                        "description": f"Primary milestone execution task for {goal_title}.",
                        "milestone_id": "m1",
                        "priority": 1,
                        "estimated_minutes": 45,
                        "scheduled_date": datetime.now().strftime("%Y-%m-%d")
                    }
                ]

        modes = raw.get("goal_modes") or [f"{category.upper()}_MODE", "EXECUTION_MODE"]

        return {
            "type": "GOAL_INTELLIGENCE_RESPONSE",
            "goal": {
                "goal_id": g_id,
                "title": g_info.get("title", goal_title),
                "category": category,
                "target_outcome": g_info.get("target_outcome", f"Successfully achieve {goal_title}"),
                "priority": g_info.get("priority", "HIGH"),
                "deadline": g_info.get("deadline", "Target 90 Days"),
                "status": "active"
            },
            "goal_modes": modes,
            "analysis": raw.get("analysis", {
                "desired_outcome": f"Complete {goal_title}",
                "current_state": "Planning & Initialization",
                "gap": "Action execution & milestone completion required",
                "learning_required": "learning" in category.lower() or "study" in goal_title.lower()
            }),
            "milestones": milestones,
            "tasks": tasks,
            "content": raw.get("content", [
                {
                    "type": "CHECKLIST",
                    "title": f"Milestone Action Checklist",
                    "items": [t["title"] for t in tasks]
                }
            ]),
            "visualizations": raw.get("visualizations", []),
            "recommendations": raw.get("recommendations", [
                {"title": f"Begin Task: {tasks[0]['title']}", "action": "Start immediately"}
            ]),
            "next_action": raw.get("next_action", {
                "type": "EXECUTE",
                "title": tasks[0]["title"],
                "reason": "Highest priority initial action item"
            }),
            "progress_update": raw.get("progress_update", {
                "percentage": 10,
                "summary": "Goal initialized with active milestones and tasks."
            })
        }

    def _persist_analyzed_goal(self, validated: Dict[str, Any]) -> None:
        goals = self.load_goals()
        g_data = validated["goal"]
        g_id = g_data["goal_id"]

        # Convert to goals.json standard structure
        new_entry = {
            "id": g_id,
            "subject": g_data["title"],
            "title": g_data["title"],
            "category": g_data["category"],
            "status": "active",
            "created": datetime.now().isoformat(),
            "target_outcome": g_data["target_outcome"],
            "priority": g_data["priority"],
            "plan": {
                "milestones": validated.get("milestones", []),
                "next_action": validated.get("next_action", {})
            }
        }

        updated = False
        for idx, item in enumerate(goals):
            if item.get("id") == g_id or item.get("subject", "").lower() == g_data["title"].lower():
                goals[idx] = new_entry
                updated = True
                break
        if not updated:
            goals.append(new_entry)

        self.save_goals(goals)


_goal_intel_instance: Optional[UniversalGoalIntelligenceService] = None


def get_goal_intelligence_service() -> UniversalGoalIntelligenceService:
    global _goal_intel_instance
    if _goal_intel_instance is None:
        _goal_intel_instance = UniversalGoalIntelligenceService()
    return _goal_intel_instance
