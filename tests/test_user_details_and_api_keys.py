"""
tests/test_user_details_and_api_keys.py — Verification of user details persistence & dedicated learning API key
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from memory.user_details_capturer import (
    capture_user_profile_details,
    capture_user_goal,
    capture_learning_progress,
    extract_and_persist_from_text,
)
from services.learning.gemini_learning_client import GeminiLearningClient


class TestUserDetailsAndApiKeys(unittest.TestCase):
    def test_capture_user_profile_details(self):
        res = capture_user_profile_details(
            preferred_name="TestUser",
            user_type="student",
            target_exam="Placement Exam",
            subjects=["Python", "DSA"]
        )
        self.assertEqual(res.get("identity", {}).get("preferred_name"), "TestUser")
        self.assertEqual(res.get("role", {}).get("type"), "student")
        self.assertEqual(res.get("education", {}).get("target_exam"), "Placement Exam")
        self.assertIn("Python", res.get("interests", []))

    def test_capture_user_goal(self):
        goal = capture_user_goal(
            subject="Placement Preparation",
            goal_type="exam_prep",
            milestones=[{"title": "Phase 1", "tasks": ["Task A"]}]
        )
        self.assertEqual(goal.get("subject"), "Placement Preparation")
        self.assertEqual(goal.get("status"), "active")
        self.assertGreaterEqual(len(goal.get("milestones", [])), 1)

    def test_capture_learning_progress(self):
        prog = capture_learning_progress(
            subject="Placement Preparation",
            topics=["Python Fundamentals", "DSA"],
            minutes_spent=45
        )
        self.assertGreaterEqual(prog.get("total_learning_minutes", 0), 45)
        self.assertIn("Python Fundamentals", prog.get("strong_topics", []))
        self.assertEqual(prog.get("active_learning_plan", {}).get("subject"), "Placement Preparation")

    def test_extract_and_persist_from_text(self):
        txt = "My name is Sharukesh and my placement exam is tomorrow. I need Python, DSA, aptitude and logical reasoning."
        extracted = extract_and_persist_from_text(txt)
        self.assertEqual(extracted.get("name"), "Sharukesh")
        self.assertEqual(extracted.get("exam"), "Placement Preparation")
        self.assertIn("Python", extracted.get("subjects", []))

    def test_gemini_learning_client_dedicated_key(self):
        os.environ["GEMINI_LEARNING_API_KEY"] = "TEST_LEARNING_KEY_12345"
        client = GeminiLearningClient()
        self.assertEqual(client.api_key, "TEST_LEARNING_KEY_12345")


if __name__ == "__main__":
    unittest.main()
