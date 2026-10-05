"""
core/learning_renderer.py — Learning Content Renderer for JARVIS-X

Renders learning content using rich structured components (diagrams, code execution,
tables, timelines, quizzes, flowcharts, flashcards, concept cards) rather than plain text blocks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentType(str, Enum):
    TEXT             = "TEXT"
    CONCEPT_CARD     = "CONCEPT_CARD"
    DIAGRAM          = "DIAGRAM"
    FLOWCHART        = "FLOWCHART"
    TIMELINE         = "TIMELINE"
    TABLE            = "TABLE"
    CODE             = "CODE"
    INTERACTIVE_CODE = "INTERACTIVE_CODE"
    QUIZ             = "QUIZ"
    FLASHCARDS       = "FLASHCARDS"
    COMPARISON       = "COMPARISON"
    TREE             = "TREE"
    PROCESS_FLOW     = "PROCESS_FLOW"
    SIMULATION       = "SIMULATION"
    EXAMPLE          = "EXAMPLE"
    PRACTICE         = "PRACTICE"


@dataclass
class LearningComponent:
    component_type: ContentType
    title: str
    data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type.value,
            "title": self.title,
            "data": self.data,
            "summary": self.summary,
        }


class LearningContentRenderer:
    """Formats and builds rich dynamic learning UI structures for JARVIS-X."""

    @staticmethod
    def render_concept_card(title: str, definition: str, key_points: List[str], example: str = "") -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.CONCEPT_CARD,
            title=title,
            data={
                "definition": definition,
                "key_points": key_points,
                "example": example,
            },
            summary=f"Concept Card: {title}",
        )

    @staticmethod
    def render_code_studio(title: str, language: str, initial_code: str, expected_output: str = "", explanation: str = "") -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.INTERACTIVE_CODE,
            title=title,
            data={
                "language": language,
                "code": initial_code,
                "expected_output": expected_output,
                "explanation": explanation,
            },
            summary=f"Interactive Code Studio [{language}]: {title}",
        )

    @staticmethod
    def render_comparison_table(title: str, headers: List[str], rows: List[List[str]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.COMPARISON,
            title=title,
            data={
                "headers": headers,
                "rows": rows,
            },
            summary=f"Comparison Table: {title}",
        )

    @staticmethod
    def render_process_flow(title: str, steps: List[Dict[str, str]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.PROCESS_FLOW,
            title=title,
            data={
                "steps": steps, # List of {"step": 1, "title": "...", "description": "..."}
            },
            summary=f"Process Flow Diagram: {title}",
        )

    @staticmethod
    def render_quiz(title: str, questions: List[Dict[str, Any]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.QUIZ,
            title=title,
            data={
                "questions": questions, # List of {"id": 1, "question": "...", "options": [...], "correct": 0}
            },
            summary=f"Interactive Quiz: {title}",
        )

    @staticmethod
    def render_flashcards(title: str, cards: List[Dict[str, str]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.FLASHCARDS,
            title=title,
            data={
                "cards": cards, # List of {"front": "...", "back": "..."}
            },
            summary=f"Flashcards Deck: {title}",
        )
