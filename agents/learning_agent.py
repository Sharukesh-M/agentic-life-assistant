"""
agents/learning_agent.py - JARVIS-X Learning Agent

Adapts teaching difficulty based on user performance.
Works with flashcards and quiz_mode plugins.
Never jumps to advanced material when user is a beginner.
"""

from __future__ import annotations

import json
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
            "concept_status":  self._concept_status,
            "record_attempt":  self._record_attempt,
            "next_concept":    self._next_concept,
            "learning_path":   self._learning_path,
            "adapt_difficulty": self._adapt_difficulty,
        }
        handler = dispatch.get(action, self._concept_status)
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
