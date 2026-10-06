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
    ANALOGY          = "ANALOGY"
    FORMULA          = "FORMULA"
    CASE_STUDY       = "CASE_STUDY"
    PROJECT          = "PROJECT"
    CHECKLIST        = "CHECKLIST"
    SUMMARY          = "SUMMARY"
    REVISION_CARD    = "REVISION_CARD"
    ASSESSMENT       = "ASSESSMENT"
    IMAGE_GENERATION = "IMAGE_GENERATION"


@dataclass
class LearningComponent:
    component_type: ContentType
    title: str
    data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        val = self.component_type.value if isinstance(self.component_type, ContentType) else str(self.component_type)
        return {
            "component_type": val,
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

    @staticmethod
    def render_flowchart(title: str, nodes: List[Dict[str, str]], edges: List[Dict[str, str]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.FLOWCHART,
            title=title,
            data={
                "nodes": nodes,
                "edges": edges,
            },
            summary=f"Flowchart: {title}",
        )

    @staticmethod
    def render_practice(title: str, difficulty: str, questions: List[Dict[str, Any]]) -> LearningComponent:
        return LearningComponent(
            component_type=ContentType.PRACTICE,
            title=title,
            data={
                "difficulty": difficulty,
                "questions": questions,
            },
            summary=f"Practice Exercise [{difficulty}]: {title}",
        )

    @staticmethod
    def parse_learning_response(data: Dict[str, Any]) -> List[LearningComponent]:
        """Parses a structured LEARNING_RESPONSE object into a list of LearningComponents."""
        components: List[LearningComponent] = []

        if not isinstance(data, dict):
            return components

        # 1. Goal & Personalization Header
        goal_info = data.get("goal", {})
        pers_info = data.get("personalization", {})
        obj_info = data.get("learning_objective", {})

        if goal_info or pers_info or obj_info:
            header_summary = (
                f"Goal: {goal_info.get('goal_title', 'General Learning')} | "
                f"Level: {pers_info.get('user_level', 'Adaptive')} | "
                f"Time: {pers_info.get('available_time_minutes', 30)}m"
            )
            reason = pers_info.get("learning_reason", "")
            key_pts = [f"Connection: {goal_info.get('connection_to_goal', '')}"] if goal_info.get('connection_to_goal') else []
            if obj_info.get("description"):
                key_pts.append(f"Objective: {obj_info.get('description')}")
            components.append(
                LearningContentRenderer.render_concept_card(
                    title=obj_info.get("title", goal_info.get("goal_title", "Learning Objective")),
                    definition=reason or obj_info.get("description", "Goal-oriented learning session."),
                    key_points=key_pts,
                )
            )

        # 2. Content blocks
        raw_contents = data.get("content", [])
        if isinstance(raw_contents, list):
            for item in raw_contents:
                if not isinstance(item, dict):
                    continue
                ctype_str = str(item.get("type", "CONCEPT_CARD")).upper()
                title = item.get("title", item.get("name", "Learning Unit"))
                try:
                    ctype = ContentType(ctype_str)
                except ValueError:
                    ctype = ContentType.CONCEPT_CARD

                comp_data = {k: v for k, v in item.items() if k not in ("type", "title")}
                components.append(
                    LearningComponent(
                        component_type=ctype,
                        title=title,
                        data=comp_data,
                        summary=f"{ctype.value}: {title}",
                    )
                )

        # 3. Assessment / Quiz
        assessment = data.get("assessment", {})
        if isinstance(assessment, dict) and assessment.get("questions"):
            components.append(
                LearningContentRenderer.render_quiz(
                    title=f"Assessment for {obj_info.get('title', 'Today\'s Lesson')}",
                    questions=assessment.get("questions", []),
                )
            )

        # 4. Visualization Requests (Flowcharts, Diagrams)
        viz_requests = data.get("visualization_requests", [])
        if isinstance(viz_requests, list):
            for viz in viz_requests:
                if not isinstance(viz, dict):
                    continue
                vtype = viz.get("type", "FLOWCHART").upper()
                vdata = viz.get("data", {})
                vtitle = viz.get("purpose", viz.get("title", "Concept Visualization"))
                if vtype == "FLOWCHART":
                    components.append(
                        LearningContentRenderer.render_flowchart(
                            title=vtitle,
                            nodes=vdata.get("nodes", []),
                            edges=vdata.get("edges", []),
                        )
                    )
                else:
                    components.append(
                        LearningComponent(
                            component_type=ContentType.DIAGRAM,
                            title=vtitle,
                            data=vdata,
                            summary=f"Diagram: {vtitle}",
                        )
                    )

        return components

