"""
End-to-End Integration Tests for JARVIX Text Agent Pipeline.
Verifies User Request -> Context -> Orchestrator -> LLM -> Capability Execution -> Schema Validation -> Response.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext
from app.llm.provider import MockLLMProvider

class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        self.mock_provider = MockLLMProvider()
        self.orchestrator = JARVIXOrchestrator(llm_provider=self.mock_provider)

    def test_e2e_planning_pipeline(self):
        """Test full pipeline for a 30-day goal planning request."""
        user_request = "Create a 30-day plan to learn Generative AI."
        context = AgentContext(user_id="test_user")

        result = self.orchestrator.execute_pipeline(user_request, context)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["intent"], "goal_planning")
        self.assertIn("Planning", result["required_capabilities"])
        self.assertIsNotNone(result["result"])
        self.assertTrue(result["result"]["success"])
        self.assertEqual(result["result"]["type"], "plan")

        plan_data = result["result"]["data"]
        # Handle both dataclass and dict objects
        milestones = plan_data.get("milestones") if isinstance(plan_data, dict) else plan_data.milestones
        self.assertGreater(len(milestones), 0)

    def test_e2e_general_conversation_pipeline(self):
        """Test full pipeline for general conversation greeting."""
        user_request = "Hello JARVIX, explain what you can do."
        context = AgentContext(user_id="test_user")

        result = self.orchestrator.execute_pipeline(user_request, context)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["intent"], "general_conversation")
        self.assertIn("General Conversation", result["required_capabilities"])
        self.assertIsNotNone(result["result"])
        self.assertTrue(result["result"]["success"])
        self.assertIn("JARVIX", result["result"]["response"])

    def test_e2e_safety_confirmation_gating(self):
        """Test full pipeline when action requires explicit user confirmation."""
        user_request = "Schedule a meeting on my primary Google Calendar for 3pm."
        context = AgentContext(user_id="test_user")

        result = self.orchestrator.execute_pipeline(user_request, context)

        self.assertEqual(result["status"], "requires_confirmation")
        self.assertEqual(result["intent"], "calendar_schedule")
        self.assertIsNotNone(result["confirmation_prompt"])

if __name__ == "__main__":
    unittest.main()
