"""
agents/learning_agent.py - JARVIS-X Learning Agent

Adapts teaching difficulty based on user performance.
Works with flashcards and quiz_mode plugins.
Never jumps to advanced material when user is a beginner.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from agents.base_agent import AgentResult, BaseAgent


# ---------------------------------------------------------------------------
# ConceptRecord - tracks mastery of a learning concept
# ---------------------------------------------------------------------------

@dataclass
class ConceptRecord:
    """Learning progress for one concept within a goal."""
    concept: str
    goal_subject: str
    level: str = "beginner"        # beginner | intermediate | advanced
    last_tested: Optional[str] = None
    attempts: int = 0
    successes: int = 0
    consecutive_success: int = 0
    consecutive_failure: int = 0
    notes: str = ""

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return round(self.successes / self.attempts, 2)

    def record_attempt(self, passed: bool) -> None:
        self.attempts += 1
        self.last_tested = datetime.now().isoformat()
        if passed:
            self.successes += 1
            self.consecutive_success += 1
            self.consecutive_failure = 0
        else:
            self.consecutive_failure += 1
            self.consecutive_success = 0

    def should_advance(self) -> bool:
        """True when the user has mastered this level."""
        return self.consecutive_success >= 3 and self.success_rate >= 0.8

    def should_simplify(self) -> bool:
        """True when the user is struggling."""
        return self.consecutive_failure >= 2 or (
            self.attempts >= 4 and self.success_rate < 0.4
        )

    def next_level(self) -> str:
        levels = ["beginner", "intermediate", "advanced"]
        idx = levels.index(self.level) if self.level in levels else 0
        return levels[min(idx + 1, len(levels) - 1)]

    def prev_level(self) -> str:
        levels = ["beginner", "intermediate", "advanced"]
        idx = levels.index(self.level) if self.level in levels else 1
        return levels[max(idx - 1, 0)]

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# ConceptStore
# ---------------------------------------------------------------------------

_CONCEPTS_PATH = (
    Path(__file__).resolve().parent.parent / "memory" / "concepts.json"
)
_concepts_lock = Lock()


def _load_concepts() -> list[dict]:
    try:
        if _CONCEPTS_PATH.exists():
            data = json.loads(_CONCEPTS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_concepts(records: list[ConceptRecord]) -> None:
    try:
        _CONCEPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONCEPTS_PATH.write_text(
            json.dumps([r.to_dict() for r in records], indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[LearningAgent] Concept save error: {exc}")


def _find_concept(records: list[ConceptRecord], concept: str, goal: str) -> Optional[ConceptRecord]:
    c, g = concept.lower(), goal.lower()
    return next(
        (r for r in records if r.concept.lower() == c and r.goal_subject.lower() == g),
        None,
    )


# ---------------------------------------------------------------------------
# LearningAgent
# ---------------------------------------------------------------------------

class LearningAgent(BaseAgent):
    """Adaptive learning path management.

    Tracks which concepts have been learned/mastered and adjusts difficulty.
    Works alongside flashcards and quiz_mode plugins (does not replace them).
    """

    name = "learning_agent"
    description = (
        "Track learning progress per concept. Adapt difficulty based on "
        "quiz/exercise results. Never advance beyond user's current level."
    )
    capabilities = [
        "learning",
        "generate_content",
        "generate_daily_lesson",
        "generate_roadmap",
        "adapt_difficulty",
        "concept_status",
        "record_attempt",
        "next_concept",
        "learning_path",
    ]
    priority = 7

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args", {})
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "generate_content":      self._generate_personalized_content,
            "generate_daily_lesson": self._generate_personalized_content,
            "generate_lesson":       self._generate_personalized_content,
            "generate_roadmap":      self._generate_roadmap,
            "concept_status":        self._concept_status,
            "record_attempt":        self._record_attempt,
            "next_concept":          self._next_concept,
            "learning_path":         self._learning_path,
            "adapt_difficulty":      self._adapt_difficulty,
        }
        handler = dispatch.get(action, self._generate_personalized_content if action in ("learning", "study", "teach") else self._concept_status)
        return handler(args, context)

    def _concept_status(self, args: dict, ctx: dict) -> AgentResult:
        goal = args.get("goal_subject", args.get("subject", "")).strip()
        with _concepts_lock:
            raw = _load_concepts()
        records = [ConceptRecord(**d) for d in raw]
        if goal:
            records = [r for r in records if r.goal_subject.lower() == goal.lower()]
        if not records:
            return AgentResult(message="No learning progress tracked yet for this goal.")

        lines = []
        for r in records:
            line = f"• {r.concept} [{r.level}] — {int(r.success_rate*100)}% success rate"
            if r.should_advance():
                line += " ✓ (ready to advance)"
            elif r.should_simplify():
                line += " ⚠ (needs simplification)"
            lines.append(line)

        return AgentResult(
            message=f"Learning progress for '{goal}':\n" + "\n".join(lines),
            data={"concepts": [r.to_dict() for r in records]},
        )

    def _record_attempt(self, args: dict, ctx: dict) -> AgentResult:
        concept = args.get("concept", "").strip()
        goal = args.get("goal_subject", args.get("subject", "")).strip()
        passed = bool(args.get("passed", args.get("success", False)))

        if not concept or not goal:
            return AgentResult(needs_input=True, missing_field="concept",
                               message="Which concept and goal?")

        with _concepts_lock:
            raw = _load_concepts()
            records = [ConceptRecord(**d) for d in raw]
            rec = _find_concept(records, concept, goal)
            if rec is None:
                rec = ConceptRecord(concept=concept, goal_subject=goal)
                records.append(rec)

            rec.record_attempt(passed)

            # Auto-advance or simplify
            msg = f"Recorded {'pass' if passed else 'fail'} for '{concept}'."
            if passed and rec.should_advance():
                old_level = rec.level
                rec.level = rec.next_level()
                msg += f" Advancing from {old_level} to {rec.level}."
            elif not passed and rec.should_simplify():
                old_level = rec.level
                rec.level = rec.prev_level()
                msg += (
                    f" Stepping back to {rec.level} — "
                    "let's reinforce the basics before moving on."
                )

            _save_concepts(records)

        return AgentResult(
            message=msg,
            data={"concept": concept, "level": rec.level,
                  "success_rate": rec.success_rate},
        )

    def _next_concept(self, args: dict, ctx: dict) -> AgentResult:
        """Suggest the next concept to study."""
        goal = args.get("goal_subject", args.get("subject", "")).strip()
        with _concepts_lock:
            raw = _load_concepts()
        records = [ConceptRecord(**d) for d in raw
                   if not goal or d.get("goal_subject", "").lower() == goal.lower()]

        # Suggest concepts that need simplification first, then incomplete ones
        struggling = [r for r in records if r.should_simplify()]
        if struggling:
            r = struggling[0]
            return AgentResult(
                message=(
                    f"Let's revisit '{r.concept}' at the {r.level} level — "
                    "some more practice would help here."
                ),
                data={"concept": r.concept, "level": r.level},
            )

        # Concepts not yet mastered
        not_mastered = [r for r in records if not r.should_advance()]
        if not_mastered:
            r = not_mastered[0]
            return AgentResult(
                message=f"Continue with '{r.concept}' at {r.level} level.",
                data={"concept": r.concept, "level": r.level},
            )

        return AgentResult(
            message="All tracked concepts are progressing well. Add new concepts to continue.",
        )

    def _learning_path(self, args: dict, ctx: dict) -> AgentResult:
        """Return a structured learning path suggestion for a goal."""
        goal = args.get("goal_subject", args.get("subject", "")).strip()
        if not goal:
            return AgentResult(needs_input=True, missing_field="subject")

        # Generic learning path structure (customized per goal type in Phase 3)
        path = {
            "goal": goal,
            "phases": [
                {"phase": 1, "label": "Fundamentals", "concepts": ["Core concepts", "Basic syntax/theory", "First exercises"]},
                {"phase": 2, "label": "Application", "concepts": ["Worked examples", "Problem solving", "Mini-project"]},
                {"phase": 3, "label": "Depth", "concepts": ["Advanced topics", "Edge cases", "Real-world application"]},
            ],
        }
        msg = (
            f"Learning path for '{goal}':\n"
            + "\n".join(
                f"  Phase {p['phase']}: {p['label']} — {', '.join(p['concepts'])}"
                for p in path["phases"]
            )
        )
        return AgentResult(message=msg, data=path)

    def _adapt_difficulty(self, args: dict, ctx: dict) -> AgentResult:
        """Evaluate all concepts and return difficulty recommendations."""
        goal = args.get("goal_subject", "").strip()
        with _concepts_lock:
            raw = _load_concepts()
        records = [ConceptRecord(**d) for d in raw
                   if not goal or d.get("goal_subject", "").lower() == goal.lower()]
        recs = []
        for r in records:
            if r.should_advance():
                recs.append(f"• {r.concept}: ready for next level ({r.next_level()})")
            elif r.should_simplify():
                recs.append(f"• {r.concept}: needs easier material ({r.prev_level()})")
        if not recs:
            return AgentResult(message="Difficulty is well-calibrated. Keep going.")
        return AgentResult(
            message="Difficulty recommendations:\n" + "\n".join(recs),
        )

    # ---------------------------------------------------------------------------
    # Personalized Goal-Aware Content Generation Engine
    # ---------------------------------------------------------------------------

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).resolve().parent / "learning_agent_prompt.txt"
        try:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        except Exception:
            pass
        return "You are the Learning Intelligence Engine of JARVIS-X. Transform user context and goals into structured LEARNING_RESPONSE JSON."

    def _build_user_context(self, ctx: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        """Assembles structured USER_CONTEXT from user profile, goals, concepts, and tasks."""
        profile = {}
        try:
            from memory.profile_manager import load_profile
            profile = load_profile()
        except Exception:
            pass

        goals = []
        try:
            from agents.goal_agent import GoalAgent
            goal_agent = GoalAgent()
            goals = goal_agent._load_goals()
        except Exception:
            pass

        requested_subject = args.get("subject", args.get("topic", args.get("goal_title", ""))).strip()

        current_goal = None
        if requested_subject:
            for g in goals:
                if requested_subject.lower() in g.get("title", "").lower() or requested_subject.lower() in g.get("description", "").lower():
                    current_goal = g
                    break
        if not current_goal and goals:
            current_goal = goals[0]

        with _concepts_lock:
            raw_concepts = _load_concepts()
        records = [ConceptRecord(**d) for d in raw_concepts]
        completed_topics = [r.concept for r in records if r.should_advance()]
        weak_topics = [r.concept for r in records if r.should_simplify()]
        strong_topics = [r.concept for r in records if r.success_rate >= 0.75]

        today_tasks = []
        try:
            from memory.task_store import get_task_store
            store = get_task_store()
            today_tasks = [t.to_dict() for t in store.today()]
        except Exception:
            pass

        user_context = {
            "identity": {
                "name": profile.get("identity", {}).get("preferred_name", "User"),
                "role": profile.get("role", {}).get("type", "Learner"),
                "profession": profile.get("profession", {}),
                "education": profile.get("education", {}),
            },
            "goals": goals,
            "current_goal": current_goal or {
                "id": "g-default",
                "title": requested_subject or "Software Development & Placement Prep",
                "description": "Master technical skills and placement problem solving.",
                "priority": "high",
                "deadline": "2026-12-31",
                "target_outcome": "Complete placement DSA and system preparation."
            },
            "current_skill_level": {
                "overall": "intermediate" if strong_topics else "beginner",
                "topic_levels": {r.concept: r.level for r in records},
                "experience": "active"
            },
            "learning_preferences": profile.get("preferences", {}).get("learning", {
                "style": "visual_and_practical",
                "visual": True,
                "examples": True,
                "practice": True,
                "difficulty": "adaptive",
                "language": "English",
                "pace": "moderate"
            }),
            "availability": {
                "daily_minutes": args.get("time_minutes", 45),
                "preferred_times": ["evening"],
                "schedule": {}
            },
            "progress": {
                "completed_topics": completed_topics,
                "weak_topics": weak_topics,
                "strong_topics": strong_topics,
                "recent_attempts": [r.to_dict() for r in records[-5:]],
                "completion_rate": f"{int((len(completed_topics)/(len(records) or 1))*100)}%"
            },
            "current_roadmap": {},
            "current_task": today_tasks[0] if today_tasks else {},
            "previous_learning_context": {},
            "user_preferences": profile.get("preferences", {}),
            "current_request": args.get("query", args.get("request", f"Teach {requested_subject or 'next topic'}"))
        }
        return user_context

    def _generate_personalized_content(self, args: dict, ctx: dict) -> AgentResult:
        """Generates goal-aware personalized learning content using LearningIntelligenceService."""
        user_ctx = self._build_user_context(ctx, args)
        subject = args.get("subject", user_ctx["current_goal"].get("title", "DSA & Software Development"))

        try:
            from services.learning import get_learning_intelligence_service
            intel_svc = get_learning_intelligence_service()
            lesson_res = intel_svc.process_learning_request("lesson", user_ctx, subject=subject)
            
            # Format into response_json
            response_json = {
                "type": "LEARNING_RESPONSE",
                "goal": {
                    "goal_id": user_ctx["current_goal"].get("id", "g-1"),
                    "goal_title": user_ctx["current_goal"].get("title", subject),
                    "connection_to_goal": f"Directly builds key skills for {user_ctx['current_goal'].get('title', subject)}."
                },
                "personalization": {
                    "user_level": user_ctx.get("current_skill_level", {}).get("overall", "beginner"),
                    "learning_reason": f"Targeted lesson for {subject} based on your current goal.",
                    "available_time_minutes": user_ctx.get("availability", {}).get("daily_minutes", 30),
                    "deadline": user_ctx["current_goal"].get("deadline", "Upcoming"),
                    "priority": user_ctx["current_goal"].get("priority", "high")
                },
                "learning_objective": {
                    "id": lesson_res.get("lesson_id", "lsn-1"),
                    "title": lesson_res.get("objective", f"Understanding {subject}"),
                    "description": lesson_res.get("objective", f"Master core concepts for {subject}"),
                    "estimated_minutes": lesson_res.get("estimated_minutes", 30)
                },
                "content": lesson_res.get("blocks", []),
                "assessment": {
                    "type": "QUIZ",
                    "questions": []
                },
                "next_step": {
                    "type": "PRACTICE_EXERCISE",
                    "title": f"Practice {subject}",
                    "reason": "Reinforce understanding through exercises."
                },
                "task_recommendation": {
                    "required": True,
                    "title": f"Complete {subject} lesson",
                    "estimated_minutes": lesson_res.get("estimated_minutes", 30)
                },
                "visualization_requests": [],
                "image_generation_requests": lesson_res.get("image_generation_requests", [])
            }
        except Exception as exc:
            print(f"[LearningAgent] Intelligence Service note: {exc}")
            response_json = self._build_fallback_learning_response(user_ctx, subject)

        from core.learning_renderer import LearningContentRenderer
        components = LearningContentRenderer.parse_learning_response(response_json)

        try:
            from core.workspace_manager import get_workspace_manager
            get_workspace_manager().open_learning_workspace()
        except Exception:
            pass

        goal_title = response_json.get("goal", {}).get("goal_title", subject)
        learning_obj = response_json.get("learning_objective", {}).get("title", f"Mastering {subject}")
        connection = response_json.get("goal", {}).get("connection_to_goal", "")

        summary_msg = (
            f"Generated personalized learning session for '{goal_title}':\n"
            f"• Objective: {learning_obj}\n"
            f"• Connection: {connection}\n"
            f"• Components: {len(components)} interactive module(s) loaded into Learning Workspace."
        )

        return AgentResult(
            message=summary_msg,
            data={
                "response": response_json,
                "components": [c.to_dict() for c in components]
            }
        )

    def _generate_roadmap(self, args: dict, ctx: dict) -> AgentResult:
        """Generates dynamic goal-aware learning roadmap using LearningIntelligenceService."""
        user_ctx = self._build_user_context(ctx, args)
        goal_info = user_ctx.get("current_goal", {})
        goal_title = goal_info.get("title", args.get("subject", "Goal Roadmap"))

        try:
            from services.learning import get_learning_intelligence_service
            intel_svc = get_learning_intelligence_service()
            roadmap = intel_svc.process_learning_request("roadmap", user_ctx, goal_title=goal_title)
        except Exception as exc:
            print(f"[LearningAgent] Roadmap service note: {exc}")
            roadmap = {
                "goal": goal_title,
                "target_outcome": goal_info.get("target_outcome", f"Achieve mastery in {goal_title}"),
                "deadline": goal_info.get("deadline", "TBD"),
                "milestones": [
                    {
                        "id": "m1",
                        "title": "Phase 1: Foundations & Core Concepts",
                        "duration_days": 7,
                        "modules": ["Theory & Syntax", "Basic Worked Examples", "Diagnostic Quiz"],
                        "assessment": "Foundational Assessment"
                    }
                ]
            }

        try:
            from core.workspace_manager import get_workspace_manager
            get_workspace_manager().open_goals_workspace()
        except Exception:
            pass

        milestone_count = len(roadmap.get("milestones", []))
        return AgentResult(
            message=f"Generated goal-aware dynamic roadmap for '{goal_title}' across {milestone_count} milestone(s).",
            data={"roadmap": roadmap}
        )

    def _build_fallback_learning_response(self, user_ctx: dict, subject: str) -> dict:
        goal_info = user_ctx.get("current_goal", {})
        return {
            "type": "LEARNING_RESPONSE",
            "goal": {
                "goal_id": goal_info.get("id", "g-1"),
                "goal_title": goal_info.get("title", subject),
                "connection_to_goal": f"This topic directly builds core capabilities required for {goal_info.get('title', subject)}."
            },
            "personalization": {
                "user_level": user_ctx.get("current_skill_level", {}).get("overall", "beginner"),
                "learning_reason": f"Targeted preparation for {goal_info.get('title', subject)} based on active progress.",
                "available_time_minutes": user_ctx.get("availability", {}).get("daily_minutes", 30),
                "deadline": goal_info.get("deadline", "Upcoming"),
                "priority": goal_info.get("priority", "high")
            },
            "roadmap_update": {
                "required": False,
                "reason": "On track with current roadmap.",
                "changes": []
            },
            "learning_objective": {
                "id": f"obj-{int(datetime.now().timestamp())}",
                "title": f"Understanding {subject} Fundamentals & Patterns",
                "description": f"Learn practical applications and problem-solving techniques for {subject}.",
                "estimated_minutes": user_ctx.get("availability", {}).get("daily_minutes", 30)
            },
            "content": [
                {
                    "type": "CONCEPT_CARD",
                    "title": f"{subject} Core Concepts",
                    "content": f"{subject} forms the structural foundation needed for high-efficiency problem solving and practical application.",
                    "importance": "Crucial prerequisite for interview assessment and daily execution."
                },
                {
                    "type": "EXAMPLE",
                    "title": "Practical Worked Example",
                    "content": f"Step 1: Define requirements for {subject}.\nStep 2: Implement core logic cleanly.\nStep 3: Test with edge cases."
                },
                {
                    "type": "PRACTICE",
                    "difficulty": user_ctx.get("current_skill_level", {}).get("overall", "beginner"),
                    "questions": [
                        {
                            "id": 1,
                            "question": f"What is the primary advantage of applying {subject} structured patterns?",
                            "options": [
                                "Reduces algorithmic complexity and improves readability",
                                "Increases execution delay",
                                "Eliminates the need for testing",
                                "None of the above"
                            ],
                            "correct": 0
                        }
                    ]
                }
            ],
            "assessment": {
                "type": "QUIZ",
                "questions": [
                    {
                        "id": 1,
                        "question": f"Which approach best optimizes {subject} operations?",
                        "options": [
                            "In-place transformation and fast index lookup",
                            "Nested linear iteration without caching",
                            "Ignoring data boundaries",
                            "Random sampling"
                        ],
                        "correct": 0
                    }
                ]
            },
            "next_step": {
                "type": "PRACTICE_EXERCISE",
                "title": f"Solve 3 practice problems on {subject}",
                "reason": "Reinforce understanding through hands-on implementation."
            },
            "task_recommendation": {
                "required": True,
                "title": f"Complete {subject} practice module",
                "estimated_minutes": 25
            },
            "visualization_requests": [
                {
                    "type": "FLOWCHART",
                    "purpose": f"Process flow for {subject} execution",
                    "data": {
                        "nodes": [
                            {"id": "1", "label": "Initialize State"},
                            {"id": "2", "label": "Process Inputs"},
                            {"id": "3", "label": "Verify Output"}
                        ],
                        "edges": [
                            {"from": "1", "to": "2"},
                            {"from": "2", "to": "3"}
                        ]
                    }
                }
            ],
            "image_generation_requests": []
        }
