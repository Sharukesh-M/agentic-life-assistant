"""
Unit Tests for LLM Provider Abstraction and Configuration.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.llm.config import LLMConfig
from app.llm.response import LLMResponse
from app.llm.provider import MockLLMProvider, get_llm_provider

class TestLLMProvider(unittest.TestCase):

    def test_mock_llm_provider_general_conversation(self):
        provider = MockLLMProvider()
        resp = provider.generate("Hello JARVIX, what can you do?")
        self.assertTrue(resp.success)
        self.assertEqual(resp.provider, "mock")
        self.assertIn("JARVIX", resp.text)

    def test_mock_llm_provider_orchestration_routing(self):
        provider = MockLLMProvider()
        resp = provider.generate(
            prompt="Create a 30-day plan to learn Generative AI.",
            system_prompt="You are the JARVIX Orchestrator.",
            response_format_json=True
        )
        self.assertTrue(resp.success)
        self.assertIsNotNone(resp.parsed_json)
        self.assertEqual(resp.parsed_json.get("intent"), "goal_planning")

    def test_mock_llm_provider_planning(self):
        provider = MockLLMProvider()
        resp = provider.generate(
            prompt="GOAL: Learn Generative AI",
            system_prompt="You are the JARVIX Planning Agent.",
            response_format_json=True
        )
        self.assertTrue(resp.success)
        self.assertIsNotNone(resp.parsed_json)
        self.assertEqual(resp.parsed_json.get("status"), "plan")
        self.assertGreater(len(resp.parsed_json.get("milestones", [])), 0)

    def test_get_llm_provider_fallback(self):
        config = LLMConfig(provider="mock", model="test-model")
        provider = get_llm_provider(config)
        self.assertIsInstance(provider, MockLLMProvider)

if __name__ == "__main__":
    unittest.main()
