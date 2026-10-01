"""
tests/test_phase6_skill_injection.py - JARVIS-X Phase 6 Skill Context Injection Tests

Tests skill context block formatting, trigger lookup, and integration into
Orchestrator and _execute_tool responses.
"""

import pytest
from core.skill_loader import get_skill_registry, SkillRecord
from core.orchestrator import get_orchestrator, OrchestratorRequest, reset_orchestrator
from core.agent_bootstrap import bootstrap


@pytest.fixture(autouse=True)
def setup_bootstrap():
    reset_orchestrator()
    bootstrap()
    yield
    reset_orchestrator()


def test_skill_as_context_block_formatting():
    record = SkillRecord(
        name="test_skill",
        description="A test skill for injection",
        purpose="Verify formatting",
        instructions="Always respond politely.",
    )

    block = record.as_context_block()
    assert "[SKILL: TEST_SKILL]" in block
    assert "Purpose: Verify formatting" in block
    assert "Always respond politely." in block
    assert "[/SKILL: TEST_SKILL]" in block


def test_orchestrator_returns_skill_name():
    orch = get_orchestrator()
    req = OrchestratorRequest(tool_name="goal_tracker", tool_args={"action": "list"})
    decision = orch.route(req)

    assert decision.handled is True
    assert decision.skill_name == "goal_management"


def test_skill_registry_lookup_and_context_injection():
    registry = get_skill_registry()
    skill = registry.get("goal_management")
    assert skill is not None

    block = skill.as_context_block()
    assert "[SKILL: GOAL_MANAGEMENT]" in block
    assert len(block) > 50


def test_skill_context_injected_in_orchestrator_decision():
    orch = get_orchestrator()
    req = OrchestratorRequest(tool_name="pomodoro_timer", tool_args={"action": "start"})
    decision = orch.route(req)

    assert decision.handled is True
    assert decision.skill_name == "task_planning"
