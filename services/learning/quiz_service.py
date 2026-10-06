"""
services/learning/quiz_service.py — Quiz Generation, Adaptive Quizzing & Mock Test Engine

Supports MCQ, multiple-select, true/false, code-output, debugging, scenario-based questions,
adaptive difficulty, and complete mock tests.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class QuizService:
    """Manages adaptive quiz creation, evaluation, and mock test generation."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def generate_quiz(
        self,
        user_context: Dict[str, Any],
        topic_title: str,
        num_questions: int = 3,
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates an adaptive quiz for a topic."""
        level = difficulty or user_context.get("current_skill_level", {}).get("overall", "beginner")
        goal_title = user_context.get("current_goal", {}).get("title", "General Skill")

        prompt = f"""
Generate an adaptive quiz for topic: "{topic_title}"
Goal: "{goal_title}"
Target Level: "{level}"
Number of Questions: {num_questions}

Question types supported: MCQ, TRUE_FALSE, CODE_OUTPUT, SCENARIO

Return JSON:
{{
  "quiz_id": "qz-101",
  "topic_title": "{topic_title}",
  "difficulty": "{level}",
  "questions": [
    {{
      "id": 1,
      "type": "MCQ",
      "question": "Sample question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct": 0,
      "explanation": "Detailed explanation of correct answer."
    }}
  ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or not res.get("questions"):
            res = self._build_fallback_quiz(topic_title, level, num_questions)

        qid = res.get("quiz_id") or f"qz-{int(datetime.now().timestamp())}"
        quiz_data = {
            "quiz_id": qid,
            "topic_title": topic_title,
            "difficulty": level,
            "questions": res.get("questions", []),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.store.save_quiz(quiz_data)
        return quiz_data

    def evaluate_quiz_submission(
        self,
        quiz_id: str,
        user_answers: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluates quiz submission, updates accuracy stats, and recommends next level."""
        quizzes = self.store.load_quizzes()
        quiz = next((q for q in quizzes if q.get("quiz_id") == quiz_id), None)

        if not quiz:
            return {
                "score": 0,
                "total": 0,
                "accuracy_percent": 0,
                "recommendation": "Quiz not found"
            }

        questions = quiz.get("questions", [])
        correct_count = 0
        details = []

        for q in questions:
            qid_str = str(q.get("id"))
            user_ans = user_answers.get(qid_str)
            correct_ans = q.get("correct")

            is_correct = (user_ans == correct_ans)
            if is_correct:
                correct_count += 1

            details.append({
                "question_id": q.get("id"),
                "question": q.get("question"),
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "")
            })

        total = len(questions) or 1
        accuracy = round((correct_count / total) * 100, 1)

        recommendation = "ADVANCE" if accuracy >= 80 else ("RETRY" if accuracy < 50 else "PRACTICE")

        # Update persistent progress stats
        progress = self.store.load_progress()
        topic = quiz.get("topic_title", "General")
        progress["quiz_accuracy"][topic] = accuracy
        if recommendation == "ADVANCE" and topic not in progress["completed_topics"]:
            progress["completed_topics"].append(topic)
        elif recommendation == "RETRY" and topic not in progress["weak_topics"]:
            progress["weak_topics"].append(topic)
        self.store.save_progress(progress)

        return {
            "quiz_id": quiz_id,
            "topic_title": topic,
            "score": correct_count,
            "total": total,
            "accuracy_percent": accuracy,
            "recommendation": recommendation,
            "details": details
        }

    def generate_mock_test(
        self,
        user_context: Dict[str, Any],
        exam_title: str,
        time_limit_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Generates a complete mock test for an exam/placement goal."""
        prompt = f"""
Generate a complete mock test for: "{exam_title}"
Time Limit: {time_limit_minutes} minutes
Target Level: "{user_context.get('current_skill_level', {}).get('overall', 'intermediate')}"

Return JSON:
{{
  "mock_test_id": "mt-201",
  "exam_title": "{exam_title}",
  "time_limit_minutes": {time_limit_minutes},
  "sections": [
    {{
      "section_name": "Quantitative & Logical Aptitude",
      "questions": [
        {{
          "id": 1,
          "question": "Sample quantitative problem?",
          "options": ["Ans A", "Ans B", "Ans C", "Ans D"],
          "correct": 0,
          "explanation": "Solution step by step"
        }}
      ]
    }}
  ]
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or not res.get("sections"):
            res = {
                "mock_test_id": f"mt-{int(datetime.now().timestamp())}",
                "exam_title": exam_title,
                "time_limit_minutes": time_limit_minutes,
                "sections": [
                    {
                        "section_name": f"{exam_title} Core Assessment",
                        "questions": [
                            {
                                "id": 1,
                                "question": f"Which fundamental principle forms the baseline of {exam_title}?",
                                "options": ["Structured Execution", "Random Iteration", "Unbounded Memory", "None"],
                                "correct": 0,
                                "explanation": "Structured execution ensures optimal performance and correctness."
                            }
                        ]
                    }
                ]
            }

        return res

    def _build_fallback_quiz(self, topic_title: str, level: str, num_questions: int) -> Dict[str, Any]:
        return {
            "quiz_id": f"qz-{int(datetime.now().timestamp())}",
            "topic_title": topic_title,
            "difficulty": level,
            "questions": [
                {
                    "id": 1,
                    "type": "MCQ",
                    "question": f"What is the primary benefit of applying {topic_title}?",
                    "options": [
                        "Optimizes system performance and code structure",
                        "Increases runtime latency",
                        "Removes all testing requirements",
                        "None of the above"
                    ],
                    "correct": 0,
                    "explanation": f"{topic_title} establishes structured, efficient code execution."
                }
            ]
        }
