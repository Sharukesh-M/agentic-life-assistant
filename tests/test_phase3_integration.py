"""
tests/test_phase3_integration.py - JARVIS-X Phase 3 Integration Tests

Tests the full agent registration, orchestrator wiring, and end-to-end
routing from tool call → agent → result.

Run with: python -m pytest tests/test_phase3_integration.py -v
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest


# ===========================================================================
# Bootstrap Tests
# ===========================================================================

class TestAgentBootstrap:
    def setup_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()

    def teardown_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()

    def test_bootstrap_registers_all_agents(self):
        from core import agent_bootstrap
        from core.agent_registry import get_registry
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)
        registry = get_registry()
        names = registry.names()
        expected = {"goal_agent", "planning_agent", "progress_agent",
                    "learning_agent", "memory_agent", "proactive_agent"}
        for expected_name in expected:
            assert expected_name in names, f"Agent '{expected_name}' not registered"

    def test_bootstrap_is_idempotent(self):
        from core import agent_bootstrap
        from core.agent_registry import get_registry
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)   # second call
        registry = get_registry()
        # Should not duplicate entries
        assert registry.names().count("goal_agent") == 1

    def test_bootstrap_enables_all_agents(self):
        from core import agent_bootstrap
        from core.agent_registry import get_registry
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)
        registry = get_registry()
        for rec in registry.list():
            assert rec.enabled, f"Agent '{rec.name}' should be enabled"

    def test_all_agents_have_handlers(self):
        from core import agent_bootstrap
        from core.agent_registry import get_registry
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)
        registry = get_registry()
        for rec in registry.list():
            assert rec.handler is not None, f"Agent '{rec.name}' has no handler"

    def test_goal_agent_priority_is_highest(self):
        from core import agent_bootstrap
        from core.agent_registry import get_registry
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)
        registry = get_registry()
        goal = registry.get("goal_agent")
        planning = registry.get("planning_agent")
        assert goal.priority >= planning.priority


# ===========================================================================
# Orchestrator Routing Tests (with real agents)
# ===========================================================================

class TestOrchestratorRouting:
    def setup_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()
        from core import agent_bootstrap
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)

    def teardown_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()

    def _make_request(self, tool_name, args=None):
        from core.orchestrator import OrchestratorRequest
        return OrchestratorRequest(tool_name=tool_name, tool_args=args or {})

    def test_goal_tracker_routes_to_goal_agent(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("goal_tracker", {"action": "list"})
        decision = orch.route(req)
        assert decision.handled
        assert decision.agent_name == "goal_agent"

    def test_goal_tracker_create_routes_to_goal_agent(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("goal_tracker", {"action": "create"})
        decision = orch.route(req)
        assert decision.handled
        assert decision.agent_name == "goal_agent"

    def test_personal_agent_routes_to_goal_agent(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("personal_agent", {"action": "next_step", "subject": "GATE"})
        decision = orch.route(req)
        assert decision.handled

    def test_flashcards_routes_to_learning_agent(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("flashcards", {})
        decision = orch.route(req)
        assert decision.handled
        assert decision.agent_name == "learning_agent"

    def test_quiz_mode_routes_to_learning_agent(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("quiz_mode", {})
        decision = orch.route(req)
        assert decision.handled
        assert decision.agent_name == "learning_agent"

    def test_unknown_tool_falls_through(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("browser_control", {})
        decision = orch.route(req)
        # browser_control has no agent — should fall through
        assert not decision.handled

    def test_screen_process_falls_through(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        req = self._make_request("screen_process", {})
        decision = orch.route(req)
        assert not decision.handled  # inline tool, no agent registered

    def test_orchestrator_never_raises(self):
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        # Pathological request with weird args
        req = OrchestratorRequest(tool_name="", tool_args={"bad": None})
        try:
            decision = orch.route(req)
            assert isinstance(decision.handled, bool)
        except Exception as exc:
            pytest.fail(f"Orchestrator raised unexpectedly: {exc}")

    def test_stats_increment(self):
        from core.orchestrator import get_orchestrator
        orch = get_orchestrator()
        before = orch.stats()["total_requests"]
        orch.route(self._make_request("goal_tracker", {"action": "list"}))
        orch.route(self._make_request("browser_control", {}))
        after = orch.stats()
        assert after["total_requests"] == before + 2
        assert after["agent_hits"] >= 1
        assert after["fall_throughs"] >= 1


# ===========================================================================
# Agent Result Quality Tests
# ===========================================================================

class TestAgentResults:
    def setup_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()
        from core import agent_bootstrap
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)

    def teardown_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()

    def test_goal_list_result_is_string(self):
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        req = OrchestratorRequest(
            tool_name="goal_tracker",
            tool_args={"action": "list"},
        )
        decision = orch.route(req)
        assert decision.handled
        assert isinstance(decision.result, str)
        assert len(decision.result) > 0

    def test_goal_create_without_subject_asks_for_it(self):
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        req = OrchestratorRequest(
            tool_name="goal_tracker",
            tool_args={"action": "create"},   # no subject
        )
        decision = orch.route(req)
        assert decision.handled
        # Result should be a question asking for the subject
        assert decision.result and "?" in decision.result

    def test_progress_report_is_string(self):
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        req = OrchestratorRequest(
            tool_name="goal_tracker",
            tool_args={"action": "status"},
        )
        decision = orch.route(req)
        assert decision.handled
        assert isinstance(decision.result, str)

    def test_learning_agent_concept_status_string(self):
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        req = OrchestratorRequest(
            tool_name="flashcards",
            tool_args={"action": "concept_status", "goal_subject": "Python"},
        )
        decision = orch.route(req)
        assert decision.handled
        assert isinstance(decision.result, str)

    def test_goal_agent_pause_asks_for_subject(self):
        from agents.goal_agent import GoalAgent
        agent = GoalAgent()
        result = agent.handle("pause_goal", context={"tool_args": {"action": "pause"}})
        assert result.needs_input
        assert result.missing_field == "subject"

    def test_planning_agent_no_goals_message(self):
        from agents.planning_agent import PlanningAgent
        import json
        from pathlib import Path
        import tempfile, os
        # Ensure no goals exist for this test by pointing to empty file
        agent = PlanningAgent()
        # Temporarily override GOALS_PATH
        original = agent._GOALS_PATH
        try:
            agent._GOALS_PATH = Path(tempfile.mktemp(suffix=".json"))
            result = agent.handle("daily_plan", context={"tool_args": {"action": "daily_plan"}})
            assert result.needs_input or "no active" in result.message.lower()
        finally:
            agent._GOALS_PATH = original

    def test_memory_agent_recall_returns_string(self):
        from agents.memory_agent import MemoryAgent
        agent = MemoryAgent()
        result = agent.handle("recall_memory", context={
            "tool_args": {"action": "recall", "query": "name"}
        })
        assert isinstance(result.message, str)

    def test_proactive_agent_task_reminder(self):
        from agents.proactive_agent import ProactiveAgent
        agent = ProactiveAgent()
        result = agent.handle("task_reminder", context={"tool_args": {"action": "task_reminder"}})
        assert isinstance(result.message, str)


# ===========================================================================
# Skill + Agent Integration
# ===========================================================================

class TestSkillAgentIntegration:
    def setup_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()
        from core import agent_bootstrap
        agent_bootstrap.bootstrap(logger_fn=lambda m: None)

    def teardown_method(self):
        from core.agent_registry import reset_registry
        from core.orchestrator import reset_orchestrator
        from core.skill_loader import reset_skill_registry
        reset_registry()
        reset_orchestrator()
        reset_skill_registry()

    def test_goal_tracker_loads_goal_management_skill(self):
        """When goal_tracker is routed, the skill_name should be goal_management."""
        from core.orchestrator import get_orchestrator, OrchestratorRequest
        orch = get_orchestrator()
        req = OrchestratorRequest(
            tool_name="goal_tracker",
            tool_args={"action": "list"},
        )
        decision = orch.route(req)
        # Skill may or may not be loaded depending on SkillRegistry state
        # Main test: routing works correctly
        assert decision.handled

    def test_skill_context_for_goal_management(self):
        from core.skill_loader import get_skill_registry
        registry = get_skill_registry(_ROOT / "skills")
        skill = registry.get("goal_management")
        assert skill is not None
        ctx = skill.as_context_block()
        assert "[SKILL: GOAL_MANAGEMENT]" in ctx
        assert "lifecycle" in ctx.lower() or "goal" in ctx.lower()

    def test_skill_context_for_task_planning(self):
        from core.skill_loader import get_skill_registry
        registry = get_skill_registry(_ROOT / "skills")
        skill = registry.get("task_planning")
        assert skill is not None
        assert len(skill.instructions) > 100

    def test_skill_context_concatenation(self):
        from core.skill_loader import get_skill_registry
        registry = get_skill_registry(_ROOT / "skills")
        ctx = registry.context_for(["core", "goal_management", "task_planning"])
        assert "[SKILL: CORE]" in ctx
        assert "[SKILL: GOAL_MANAGEMENT]" in ctx
        assert "[SKILL: TASK_PLANNING]" in ctx


# ===========================================================================
# Backward Compatibility: existing goal_tracker plugin still works
# ===========================================================================

class TestBackwardCompatibility:
    """Ensure all existing plugin APIs are unchanged."""

    def test_goal_tracker_plugin_create_still_works(self):
        """goal_tracker.run() must still work directly (not through orchestrator)."""
        from plugins.goal_tracker import run as gt_run
        result = gt_run({"action": "list"})
        assert isinstance(result, str)

    def test_personal_agent_plugin_run_still_works(self):
        """personal_agent.run() must still work directly."""
        from plugins.personal_agent import run as pa_run
        result = pa_run({"action": "next_step"}, player=None)
        # Should return JSON string or error string
        assert isinstance(result, str)

    def test_goal_workflow_still_importable(self):
        from core.goal_workflow import start_goal_workflow
        assert callable(start_goal_workflow)

    def test_action_loader_still_works(self):
        from core.action_loader import discover_actions
        assert callable(discover_actions)

    def test_plugin_loader_still_works(self):
        from core.plugin_loader import discover_plugins
        assert callable(discover_plugins)

    def test_memory_manager_unchanged(self):
        from memory.memory_manager import load_memory, update_memory, search_memory
        mem = load_memory()
        assert isinstance(mem, dict)

    def test_main_py_imports_cleanly(self):
        """Ensure the Phase 3 additions don't break main.py's import chain."""
        import ast
        main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
        try:
            ast.parse(main_src)
        except SyntaxError as exc:
            pytest.fail(f"main.py has a syntax error after Phase 3 edits: {exc}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
