"""
Unit & Integration Verification Suite for JARVIX Agent Architecture, Prompts, and Schemas.
"""

import sys
import os
import unittest

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agent.prompt_loader import assemble_agent_prompt, load_prompt_file
from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext
from app.agent.decision_engine import DecisionEngine
from app.schemas.planning import PlanOutput, MilestoneItem, TaskItem, ClarificationOutput
from app.schemas.orchestration import OrchestratorRouting
from app.schemas.memory import MemoryClassificationOutput
from app.schemas.goals import GoalRecord, GoalEventCorrelationOutput, EventMatchItem
from app.schemas.proactive import ProactiveMonitorOutput, ProactiveNotificationItem
from app.schemas.tool_use import ToolCallRequest, ToolExecutionResult

class TestJARVIXArchitecture(unittest.TestCase):

    def test_prompt_loader_composition(self):
        """Verify dynamic prompt loader combines Core + Overlays + Specialist Prompt."""
        prompt = assemble_agent_prompt("planning/planning_agent.md")
        self.assertIn("You are JARVIX", prompt)
        self.assertIn("HALLUCINATION PREVENTION OVERLAY", prompt)
        self.assertIn("SAFETY & CONFIRMATION OVERLAY", prompt)
        self.assertIn("ERROR RECOVERY OVERLAY", prompt)
        self.assertIn("You are the JARVIX Planning Agent", prompt)

    def test_planning_schema_valid_plan(self):
        """Verify Pydantic validation for valid plan output."""
        plan_data = {
            "status": "plan",
            "goal": "Learn CNNs for Plant Disease Detection",
            "assumptions": ["Basic Python knowledge"],
            "milestones": [
                {
                    "title": "Dataset Preparation",
                    "description": "Download and preprocess PlantVillage dataset",
                    "tasks": [
                        {
                            "title": "Download Dataset",
                            "description": "Fetch images from source",
                            "priority": "HIGH",
                            "estimated_minutes": 60,
                            "depends_on": []
                        }
                    ]
                }
            ]
        }
        validated = PlanOutput(**plan_data)
        self.assertEqual(validated.status, "plan")
        self.assertEqual(len(validated.milestones), 1)

    def test_planning_schema_clarification(self):
        """Verify Pydantic validation for clarification request output."""
        clarification_data = {
            "status": "clarification_needed",
            "questions": ["What is your target deadline?", "How many hours per day are available?"]
        }
        validated = ClarificationOutput(**clarification_data)
        self.assertEqual(validated.status, "clarification_needed")
        self.assertEqual(len(validated.questions), 2)

    def test_reversibility_test(self):
        """Verify Decision Engine reversibility test gating."""
        self.assertTrue(DecisionEngine.is_action_reversible("local_draft", {}))
        self.assertFalse(DecisionEngine.is_action_reversible("calendar_create_event", {}))
        self.assertFalse(DecisionEngine.is_action_reversible("custom_action", {"external_visible": True}))

    def test_orchestrator_routing(self):
        """Verify Orchestrator intent classification and capability routing."""
        orchestrator = JARVIXOrchestrator()
        context = AgentContext()
        
        routing_plan = orchestrator.route_request("I want to create a plan for exam prep", context)
        self.assertEqual(routing_plan.intent, "goal_planning")
        self.assertIn("Planning", routing_plan.required_capabilities)

        routing_calendar = orchestrator.route_request("Schedule a meeting on Google Calendar for 3pm", context)
        self.assertIn("calendar", routing_calendar.intent.lower())
        self.assertTrue(routing_calendar.requires_confirmation)

if __name__ == "__main__":
    unittest.main()
