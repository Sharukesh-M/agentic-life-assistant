"""
services/learning/interactive_session_service.py — Interactive Learning Session Engine for JARVIS-X

Implements the module click contract, user/goal context loading, personalized lesson generation via Gemini,
task creation, concept progress updates, and session persistence.
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


SYSTEM_PROMPT_TEMPLATE = """You are the JARVIS-X Learning Intelligence Engine.

Your job is to transform the user's goals, current roadmap, skill level, progress, available time, preferences, and current learning module into a personalized interactive learning experience.

You are NOT a generic textbook.
You are NOT allowed to generate generic educational content when user context is available.

Your job is:
GOAL → ROADMAP → CURRENT MODULE → PERSONALIZED EXPLANATION → VISUALIZATION → EXAMPLE → PRACTICE → CODING → QUIZ → ASSESSMENT → TASK → PROGRESS → NEXT STEP

---------------------------------------------------------------
USER CONTEXT
---------------------------------------------------------------
USER_PROFILE:
{USER_PROFILE}

ACTIVE_GOALS:
{ACTIVE_GOALS}

CURRENT_GOAL:
{CURRENT_GOAL}

ROADMAP:
{ROADMAP}

CURRENT_MILESTONE:
{CURRENT_MILESTONE}

CURRENT_MODULE:
{CURRENT_MODULE}

CURRENT_TOPIC:
{CURRENT_TOPIC}

USER_SKILL_LEVEL:
{USER_SKILL_LEVEL}

LEARNING_PREFERENCES:
{LEARNING_PREFERENCES}

AVAILABLE_TIME:
{AVAILABLE_TIME}

CURRENT_SCHEDULE:
{CURRENT_SCHEDULE}

PREVIOUS_PROGRESS:
{PREVIOUS_PROGRESS}

PREVIOUS_ATTEMPTS:
{PREVIOUS_ATTEMPTS}

WEAK_AREAS:
{WEAK_AREAS}

STRONG_AREAS:
{STRONG_AREAS}

CURRENT_TASKS:
{CURRENT_TASKS}

USER_REQUEST:
{USER_REQUEST}

---------------------------------------------------------------
OUTPUT FORMAT
---------------------------------------------------------------
Return STRICT JSON.

Schema:
{{
    "type": "LEARNING_SESSION",
    "session": {{
        "title": "...",
        "estimated_minutes": 45,
        "difficulty": "beginner",
        "objective": "...",
        "why_this_matters": "..."
    }},
    "goal_connection": {{
        "goal_id": "...",
        "goal_title": "...",
        "milestone": "...",
        "module": "..."
    }},
    "content_blocks": [
        {{
            "type": "CONCEPT_CARD",
            "title": "...",
            "content": "...",
            "key_points": ["..."]
        }},
        {{
            "type": "DIAGRAM",
            "title": "...",
            "data": {{
                "type": "FLOWCHART",
                "nodes": [{{"id": "1", "label": "Start"}}, {{"id": "2", "label": "Step 1"}}],
                "edges": [{{"from": "1", "to": "2"}}]
            }}
        }},
        {{
            "type": "EXAMPLE",
            "title": "...",
            "content": "..."
        }}
    ],
    "coding": {{
        "enabled": true,
        "language": "python",
        "starter_code": "...",
        "instructions": "...",
        "test_cases": [],
        "hints": [],
        "solution": "...",
        "complexity": {{
            "time": "O(n)",
            "space": "O(1)"
        }}
    }},
    "quiz": {{
        "enabled": true,
        "questions": [
            {{
                "question_id": "q1",
                "question": "...",
                "type": "MCQ",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,
                "explanation": "...",
                "difficulty": "beginner",
                "skill_tested": "..."
            }}
        ]
    }},
    "task": {{
        "required": true,
        "title": "...",
        "description": "...",
        "estimated_minutes": 30,
        "priority": "HIGH"
    }},
    "assessment": {{}},
    "next_step": {{
        "type": "NEXT_STEP",
        "title": "...",
        "reason": "..."
    }},
    "summary": []
}}
"""


class InteractiveLearningSessionService:
    """Manages the full lifecycle of interactive module learning sessions."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()
        self.task_store = get_task_store()

    # --- Context Retrievers ---
    def get_module(self, module_id: str) -> Dict[str, Any]:
        """Resolves module info from module_id or returns structured default."""
        clean_title = module_id.replace("_", " ").replace("Task: ", "").strip()
        if not clean_title or clean_title.lower() in ("default", "unknown"):
            clean_title = "Python Lists & Data Structures"
        return {
            "module_id": module_id,
            "title": clean_title,
            "topic": clean_title,
        }

    def get_user_context(self) -> Dict[str, Any]:
        """Loads profile and availability from memory/profile.json."""
        p_path = Path(__file__).resolve().parent.parent.parent / "memory" / "profile.json"
        if p_path.exists():
            try:
                data = json.loads(p_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                pass
        return {"name": "JARVIS User", "role": "Software Developer"}

    def get_goal_context(self) -> Dict[str, Any]:
        """Loads active goals from memory/goals.json."""
        g_path = Path(__file__).resolve().parent.parent.parent / "memory" / "goals.json"
        if g_path.exists():
            try:
                data = json.loads(g_path.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    active = [g for g in data if g.get("status") == "active"]
                    return active[0] if active else data[0]
            except Exception:
                pass
        return {}

    def get_roadmap_context(self) -> Dict[str, Any]:
        """Loads current active roadmap."""
        roadmaps = self.store.load_roadmaps()
        if roadmaps:
            return roadmaps[0]
        return {
            "roadmap_id": "rdm-dsa-foundation",
            "goal_id": "goal-dev-1",
            "title": "DSA & Problem Solving Mastery",
            "milestones": [
                {"milestone_id": "m1", "title": "DSA Foundations", "status": "in_progress"},
                {"milestone_id": "m2", "title": "Advanced Data Structures", "status": "pending"}
            ]
        }

    def get_progress_context(self) -> Dict[str, Any]:
        """Loads overall learning progress metrics."""
        return self.store.load_progress()

    def get_previous_attempts(self) -> List[Dict[str, Any]]:
        """Loads concept attempt history from memory/concepts.json."""
        c_path = Path(__file__).resolve().parent.parent.parent / "memory" / "concepts.json"
        if c_path.exists():
            try:
                data = json.loads(c_path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                pass
        return []

    def get_learning_preferences(self) -> Dict[str, Any]:
        """Returns user learning preferences."""
        return {
            "style": "visual_interactive",
            "code_examples": True,
            "quiz_enabled": True,
            "explanation_depth": "practical_with_analogies"
        }

    # --- Core Module Click Contract ---
    def handle_module_click(self, module_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Executes the required module click contract:
        get_module → get_user_context → get_goal_context → get_roadmap_context →
        get_progress_context → get_previous_attempts → get_learning_preferences →
        generate_learning_session → validate_response → persist_content → return session
        """
        print(f"\n[LEARNING_MODULE_CLICK] module_id={module_id}")

        mod = self.get_module(module_id)
        user_ctx = self.get_user_context()
        goal_ctx = self.get_goal_context()
        roadmap_ctx = self.get_roadmap_context()
        progress_ctx = self.get_progress_context()
        prev_attempts = self.get_previous_attempts()
        prefs = self.get_learning_preferences()

        level = "beginner"
        if prev_attempts:
            matching = [a for a in prev_attempts if a.get("concept", "").lower() in mod["title"].lower()]
            if matching:
                level = matching[0].get("level", "beginner")

        time_avail = user_ctx.get("availability", {}).get("daily_minutes", 45)
        goal_subject = goal_ctx.get("subject") or goal_ctx.get("title") or "Software Engineering"

        print(f"[LEARNING_CONTEXT] goal='{goal_subject}' level={level} time={time_avail}m")

        # Check existing session for resume
        if not force_refresh:
            existing = self.store.get_session_by_module(module_id)
            if existing:
                print(f"[LEARNING_SESSION_LOADED] Resuming cached session {existing.get('session_id')}")
                return existing

        session_data = self.generate_learning_session(
            module=mod,
            user_ctx=user_ctx,
            goal_ctx=goal_ctx,
            roadmap_ctx=roadmap_ctx,
            progress_ctx=progress_ctx,
            prev_attempts=prev_attempts,
            prefs=prefs,
            level=level,
            available_time=time_avail,
        )

        validated_session = self.validate_response(session_data, module_id, mod["title"], goal_subject, level, time_avail)

        # Handle automatic Task creation if specified in session
        task_info = validated_session.get("task", {})
        if isinstance(task_info, dict) and task_info.get("required"):
            task_title = task_info.get("title", f"Practice {mod['title']}")
            t = Task(
                title=task_title,
                description=task_info.get("description", f"Interactive exercise for {mod['title']}"),
                duration_minutes=task_info.get("estimated_minutes", 30),
                priority=1 if task_info.get("priority") == "HIGH" else 2,
                goal_id=goal_ctx.get("id", "goal-1"),
                goal_subject=goal_subject,
                scheduled_date=datetime.now().strftime("%Y-%m-%d"),
            )
            self.task_store.add(t)
            validated_session["created_task_id"] = t.id
            print(f"[TASK_CREATED] task_id={t.id} title='{task_title}'")

        self.persist_content(validated_session)
        print(f"[LEARNING_SESSION_CREATED] session_id={validated_session.get('session_id')}\n")

        return validated_session

    def generate_learning_session(
        self,
        module: Dict[str, Any],
        user_ctx: Dict[str, Any],
        goal_ctx: Dict[str, Any],
        roadmap_ctx: Dict[str, Any],
        progress_ctx: Dict[str, Any],
        prev_attempts: List[Dict[str, Any]],
        prefs: Dict[str, Any],
        level: str,
        available_time: int,
    ) -> Dict[str, Any]:
        """Calls Gemini Learning API with system prompt template to generate structured JSON."""
        print("[GEMINI_LEARNING_REQUEST]")

        prompt = SYSTEM_PROMPT_TEMPLATE.format(
            USER_PROFILE=json.dumps(user_ctx),
            ACTIVE_GOALS=json.dumps(goal_ctx),
            CURRENT_GOAL=json.dumps(goal_ctx),
            ROADMAP=json.dumps(roadmap_ctx),
            CURRENT_MILESTONE=json.dumps(roadmap_ctx.get("milestones", [{}])[0]),
            CURRENT_MODULE=json.dumps(module),
            CURRENT_TOPIC=module["title"],
            USER_SKILL_LEVEL=level,
            LEARNING_PREFERENCES=json.dumps(prefs),
            AVAILABLE_TIME=available_time,
            CURRENT_SCHEDULE="45 mins available today",
            PREVIOUS_PROGRESS=json.dumps(progress_ctx),
            PREVIOUS_ATTEMPTS=json.dumps(prev_attempts),
            WEAK_AREAS=json.dumps(progress_ctx.get("weak_topics", [])),
            STRONG_AREAS=json.dumps(progress_ctx.get("strong_topics", [])),
            CURRENT_TASKS=json.dumps([t.to_dict() for t in self.task_store.today()]),
            USER_REQUEST=f"Generate interactive learning session for module: {module['title']}",
        )

        res = self.client.generate_json(
            prompt, system_instruction="You are the JARVIS-X Learning Intelligence Engine."
        )

        n_blocks = len(res.get("content_blocks", [])) if isinstance(res, dict) else 0
        n_quiz = len(res.get("quiz", {}).get("questions", [])) if isinstance(res, dict) and isinstance(res.get("quiz"), dict) else 0
        has_task = bool(res.get("task")) if isinstance(res, dict) else False

        print(f"[GEMINI_LEARNING_RESPONSE] blocks={n_blocks} quiz={n_quiz} task={has_task}")
        return res

    def validate_response(
        self,
        raw_res: Dict[str, Any],
        module_id: str,
        title: str,
        goal_title: str,
        level: str,
        available_time: int,
    ) -> Dict[str, Any]:
        """Ensures the response matches the required LearningSession object contract, applying clean fallbacks if needed."""
        if not isinstance(raw_res, dict) or raw_res.get("status") == "LEARNING_GENERATION_FAILED":
            raw_res = {}

        sess = raw_res.get("session") or {}
        session_title = sess.get("title") or title
        why = sess.get("why_this_matters") or (
            f"This module '{title}' is part of your {goal_title} roadmap. "
            f"Mastering it now builds the prerequisite knowledge required for advanced topics and practical projects."
        )

        content_blocks = raw_res.get("content_blocks") or [
            {
                "type": "CONCEPT_CARD",
                "title": f"Core Concept: {title}",
                "content": f"{title} provides foundational operations for building scalable applications in {goal_title}.",
                "key_points": [
                    f"Understanding core syntax and semantics of {title}",
                    "Managing memory, references, and execution flow",
                    "Applying optimal algorithms and avoiding common pitfalls"
                ]
            },
            {
                "type": "DIAGRAM",
                "title": f"{title} Operational Flowchart",
                "data": {
                    "type": "FLOWCHART",
                    "nodes": [
                        {"id": "1", "label": "Initialize State"},
                        {"id": "2", "label": f"Perform {title} Operation"},
                        {"id": "3", "label": "Verify Output & Invariants"}
                    ],
                    "edges": [
                        {"from": "1", "to": "2"},
                        {"from": "2", "to": "3"}
                    ]
                }
            },
            {
                "type": "EXAMPLE",
                "title": f"Worked Example: {title}",
                "content": f"Below is a standard pattern for working with {title}:\n\nitems = [10, 20, 30]\nitems.append(40)\nprint(f'Processed items: {{items}}')"
            }
        ]

        coding = raw_res.get("coding") or {
            "enabled": True,
            "language": "python",
            "instructions": f"Write Python code demonstrating {title} operations.",
            "starter_code": f"# {title} Interactive Practice\nnumbers = [1, 2, 3]\nnumbers.append(4)\nprint('Updated:', numbers)",
            "hints": ["Use standard Python built-in methods.", "Ensure loop condition terminates properly."],
            "solution": "numbers = [1, 2, 3]\nnumbers.append(4)\nprint('Updated:', numbers)",
            "complexity": {"time": "O(1) average", "space": "O(N)"}
        }

        quiz = raw_res.get("quiz") or {
            "enabled": True,
            "questions": [
                {
                    "question_id": "q1",
                    "question": f"What is the primary benefit of mastering {title}?",
                    "type": "MCQ",
                    "options": [
                        "Enables clean memory management & linear traversal",
                        "Decreases CPU frequency",
                        "Forces code to execute asynchronously",
                        "Deletes unused variables"
                    ],
                    "correct_answer": 0,
                    "explanation": f"Mastering {title} enables efficient element manipulation and clean data structure design.",
                    "difficulty": level,
                    "skill_tested": f"{title} Foundations"
                }
            ]
        }

        task = raw_res.get("task") or {
            "required": True,
            "title": f"Complete 5 practice problems for {title}",
            "description": f"Reinforce {title} concepts learned in this interactive session.",
            "estimated_minutes": 25,
            "priority": "HIGH"
        }

        next_step = raw_res.get("next_step") or {
            "type": "NEXT_STEP",
            "title": f"Advance to Next Milestone Topic",
            "reason": f"You have mastered the foundational concepts of {title}."
        }

        session_id = f"sess-{uuid.uuid4().hex[:8]}"

        validated = {
            "session_id": session_id,
            "module_id": module_id,
            "title": session_title,
            "user_level": level,
            "estimated_minutes": sess.get("estimated_minutes", available_time),
            "objective": sess.get("objective", f"Master {title} for {goal_title}"),
            "why_this_matters": why,
            "goal_connection": raw_res.get("goal_connection", {
                "goal_id": "goal-1",
                "goal_title": goal_title,
                "milestone": "Core Foundations",
                "module": title
            }),
            "content_blocks": content_blocks,
            "coding": coding,
            "quiz": quiz,
            "task": task,
            "assessment": raw_res.get("assessment", {}),
            "next_step": next_step,
            "summary": raw_res.get("summary", [f"Mastered core concepts of {title}."]),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        print(f"[LEARNING_CONTENT_VALIDATED] validated=True")
        return validated

    def persist_content(self, session_data: Dict[str, Any]) -> None:
        """Saves session to memory/learning_sessions.json via LearningStore."""
        self.store.save_session(session_data)

    def complete_session(self, session_id: str, quiz_score_percent: int) -> Dict[str, Any]:
        """Updates concept records, progress, and logs session completion."""
        print(f"\n[LEARNING_SESSION_COMPLETED] session_id={session_id} score={quiz_score_percent}%")
        sess = self.store.get_session(session_id)
        if not sess:
            return {"status": "error", "message": "Session not found"}

        mod_title = sess.get("title", "Concept")
        
        # Update concept record in memory/concepts.json
        c_path = Path(__file__).resolve().parent.parent.parent / "memory" / "concepts.json"
        concepts = []
        if c_path.exists():
            try:
                concepts = json.loads(c_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        found = False
        for c in concepts:
            if c.get("concept", "").lower() == mod_title.lower():
                c["attempts"] = c.get("attempts", 0) + 1
                if quiz_score_percent >= 70:
                    c["successes"] = c.get("successes", 0) + 1
                    c["consecutive_success"] = c.get("consecutive_success", 0) + 1
                    if c["consecutive_success"] >= 3:
                        c["level"] = "intermediate" if c.get("level") == "beginner" else "advanced"
                else:
                    c["consecutive_success"] = 0
                c["last_tested"] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            concepts.append({
                "concept": mod_title,
                "goal_subject": sess.get("goal_connection", {}).get("goal_title", "General"),
                "level": "beginner",
                "attempts": 1,
                "successes": 1 if quiz_score_percent >= 70 else 0,
                "consecutive_success": 1 if quiz_score_percent >= 70 else 0,
                "last_tested": datetime.now().isoformat()
            })

        c_path.write_text(json.dumps(concepts, indent=2), encoding="utf-8")
        print(f"[PROGRESS_UPDATED] concept='{mod_title}' score={quiz_score_percent}% total_attempts={len(concepts)}")

        # Update learning progress store
        progress = self.store.load_progress()
        if mod_title not in progress.get("completed_topics", []) and quiz_score_percent >= 70:
            progress.setdefault("completed_topics", []).append(mod_title)
        progress["total_learning_minutes"] = progress.get("total_learning_minutes", 0) + sess.get("estimated_minutes", 30)
        self.store.save_progress(progress)

        return {
            "status": "success",
            "concept": mod_title,
            "new_progress_percent": min(100, 40 + int(quiz_score_percent * 0.5)),
            "next_step": sess.get("next_step", {})
        }


_service_instance: Optional[InteractiveLearningSessionService] = None


def get_interactive_session_service() -> InteractiveLearningSessionService:
    global _service_instance
    if _service_instance is None:
        _service_instance = InteractiveLearningSessionService()
    return _service_instance
