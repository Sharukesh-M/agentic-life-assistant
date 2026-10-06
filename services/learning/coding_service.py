"""
services/learning/coding_service.py — Coding Learning System & Workspace Service

Generates coding lessons, coding challenges, hints, code reviews, debugging explanations, and test cases.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.learning_store import get_learning_store
from services.learning.gemini_learning_client import get_gemini_learning_client


class CodingService:
    """Manages coding challenges, code studio exercises, debugging explanations, and code reviews."""

    def __init__(self):
        self.client = get_gemini_learning_client()
        self.store = get_learning_store()

    def generate_challenge(
        self,
        user_context: Dict[str, Any],
        topic_title: str,
        language: str = "python",
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates a complete coding challenge with starter code, test cases, and hints."""
        level = difficulty or user_context.get("current_skill_level", {}).get("overall", "beginner")

        prompt = f"""
Generate a coding challenge for topic: "{topic_title}"
Language: "{language}"
Difficulty: "{level}"

Return JSON:
{{
  "challenge_id": "code-101",
  "title": "{topic_title} Challenge",
  "topic": "{topic_title}",
  "language": "{language}",
  "difficulty": "{level}",
  "problem_statement": "Detailed problem description and requirements",
  "examples": [
    {{
      "input": "sample_input",
      "output": "sample_output",
      "explanation": "Why output is produced"
    }}
  ],
  "starter_code": "def solution(data):\\n    # Write logic here\\n    pass",
  "hints": [
    "Hint 1: Think about data boundaries",
    "Hint 2: Use fast lookup"
  ],
  "test_cases": [
    {{
      "input": "data1",
      "expected_output": "res1"
    }}
  ],
  "time_complexity": "O(N)",
  "space_complexity": "O(1)"
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED" or not res.get("starter_code"):
            res = self._build_fallback_challenge(topic_title, language, level)

        cid = res.get("challenge_id") or f"code-{int(datetime.now().timestamp())}"
        challenge_data = {
            "challenge_id": cid,
            "title": res.get("title", f"{topic_title} Coding Challenge"),
            "topic": topic_title,
            "language": language,
            "difficulty": level,
            "problem_statement": res.get("problem_statement", f"Solve {topic_title} challenge."),
            "examples": res.get("examples", []),
            "starter_code": res.get("starter_code", "# Write solution\n"),
            "hints": res.get("hints", []),
            "test_cases": res.get("test_cases", []),
            "time_complexity": res.get("time_complexity", "O(N)"),
            "space_complexity": res.get("space_complexity", "O(1)"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        self.store.save_coding_challenge(challenge_data)
        return challenge_data

    def explain_code_error(
        self,
        code: str,
        error_message: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Provides AI debugging explanation and hint when code execution fails."""
        prompt = f"""
Language: {language}
User Code:
```
{code}
```
Execution Error:
{error_message}

Analyze the error and return JSON:
{{
  "error_summary": "Brief error explanation",
  "root_cause": "Why this error occurred",
  "hint": "Hint to fix the issue without giving away full answer",
  "suggested_fix": "Clean code fix"
}}
"""
        res = self.client.generate_json(prompt, system_instruction="You are the Learning Intelligence Engine of JARVIS-X.")

        if res.get("status") == "LEARNING_GENERATION_FAILED":
            res = {
                "error_summary": f"Syntax/Runtime error: {error_message[:100]}",
                "root_cause": "Variable, scope, or indentation issue in code.",
                "hint": "Check parameter types and loop boundary conditions.",
                "suggested_fix": "# Verify code structure\n" + code
            }

        return res

    def _build_fallback_challenge(self, topic_title: str, language: str, level: str) -> Dict[str, Any]:
        return {
            "challenge_id": f"code-{int(datetime.now().timestamp())}",
            "title": f"Practice: {topic_title}",
            "topic": topic_title,
            "language": language,
            "difficulty": level,
            "problem_statement": f"Implement a function that processes inputs for {topic_title} efficiently.",
            "examples": [
                {
                    "input": "[1, 2, 3]",
                    "output": "6",
                    "explanation": "Sum of elements"
                }
            ],
            "starter_code": "def solve(nums):\n    # Return output\n    return sum(nums)\n",
            "hints": [
                "Iterate through elements systematically",
                "Handle empty inputs safely"
            ],
            "test_cases": [
                {
                    "input": "[1, 2, 3]",
                    "expected_output": "6"
                }
            ],
            "time_complexity": "O(N)",
            "space_complexity": "O(1)"
        }
