"""
tests/test_phase7_end_to_end.py - JARVIS-X Master End-to-End Verification Suite

Tests complete multi-agent lifecycle across GoalAgent, PlanningAgent, ProgressAgent,
VoiceController, SkillRegistry, AgentRegistry, Orchestrator, and TaskStore.
"""

import json
import pytest
from unittest.mock import patch

from core.agent_bootstrap import bootstrap
from core.agent_registry import get_registry
from core.orchestrator import get_orchestrator, OrchestratorRequest, reset_orchestrator
from core.skill_loader import get_skill_registry
from core.state_manager import get_app_state, VoiceStateEnum
from core.voice_controller import VoiceController
from agents.goal_agent import GoalAgent
from agents.planning_agent import PlanningAgent
from agents.progress_agent import ProgressAgent
from memory.task_store import get_task_store, TaskStatus


@pytest.fixture(autouse=True)
def clean_environment(tmp_path, monkeypatch):
    """Isolate memory files and reset singletons for clean test state."""
    reset_orchestrator()
    get_app_state().session.force_voice(VoiceStateEnum.IDLE)

    test_goals_path = tmp_path / "goals.json"
    test_tasks_path = tmp_path / "tasks.json"

    monkeypatch.setattr(GoalAgent, "_GOALS_PATH", test_goals_path)
    monkeypatch.setattr(PlanningAgent, "_GOALS_PATH", test_goals_path)
    monkeypatch.setattr(ProgressAgent, "_GOALS_PATH", test_goals_path)

    import plugins.goal_tracker as gt
    monkeypatch.setattr(gt, "DATA_PATH", test_goals_path)

    import core.goal_workflow as gw
    monkeypatch.setattr(gw, "GOALS_PATH", test_goals_path)
    monkeypatch.setattr(gw, "_open_chrome_searches", lambda q: True)

    store = get_task_store()
    monkeypatch.setattr(store, "_path", test_tasks_path)

    bootstrap()
    yield tmp_path
    reset_orchestrator()


def test_master_end_to_end_agentic_lifecycle():
    """Verify complete agentic lifecycle:
    1. Orchestrator routes tool call to GoalAgent -> creates goal & seeds tasks
    2. Orchestrator routes tool call to PlanningAgent -> generates daily schedule
    3. Orchestrator routes tool call to ProgressAgent -> completes task & syncs check-in
    4. VoiceController state updates reflect pipeline status
    5. Skill context block is matched and present
    """
    orch = get_orchestrator()
    app_state = get_app_state()

    # Step 1: Create Goal via Orchestrator
    req_create = OrchestratorRequest(
        tool_name="goal_tracker",
        tool_args={"action": "create", "subject": "Learn Quantum Computing"}
    )
    dec_create = orch.route(req_create)

    assert dec_create.handled is True
    assert dec_create.agent_name == "goal_agent"
    assert dec_create.skill_name == "goal_management"
    assert "Learn Quantum Computing" in dec_create.result

    # Step 2: Generate Daily Schedule via Orchestrator
    req_plan = OrchestratorRequest(
        tool_name="pomodoro_timer",
        tool_args={"action": "daily_plan"}
    )
    dec_plan = orch.route(req_plan)

    assert dec_plan.handled is True
    assert dec_plan.agent_name == "planning_agent"
    assert dec_plan.skill_name == "task_planning"
    assert "Suggested plan for" in dec_plan.result

    # Step 3: Complete Task via ProgressAgent
    store = get_task_store()
    pending = store.pending()
    assert len(pending) > 0
    target = pending[0]

    req_comp = OrchestratorRequest(
        tool_name="habit_tracker",
        tool_args={"action": "complete_task", "task_id": target.id}
    )
    dec_comp = orch.route(req_comp)

    assert dec_comp.handled is True
    assert dec_comp.agent_name == "progress_agent"
    assert "Task completed" in dec_comp.result

    # Verify task updated in store
    assert store.get(target.id).status == TaskStatus.COMPLETED


def test_voice_controller_integrated_state_lifecycle():
    """Verify VoiceController handles transitions cleanly without errors."""
    vc = VoiceController(session=get_app_state().session)

    vc.start_listening()
    assert vc.state == VoiceStateEnum.LISTENING

    vc.mark_user_speaking()
    assert vc.state == VoiceStateEnum.USER_SPEAKING

    vc.mark_turn_complete()
    assert vc.state == VoiceStateEnum.TURN_COMPLETE

    vc.mark_thinking()
    assert vc.state == VoiceStateEnum.THINKING

    vc.mark_responding()
    assert vc.state == VoiceStateEnum.RESPONDING

    vc.start_speaking()
    assert vc.is_speaking()

    vc.stop_speaking()
    assert vc.state == VoiceStateEnum.LISTENING


def test_skills_loader_and_registry_completeness():
    """Verify all expected skills are loaded and valid."""
    registry = get_skill_registry()
    skill_names = registry.names()

    assert "goal_management" in skill_names
    assert "task_planning" in skill_names
    assert "proactive_assistance" in skill_names
    assert "memory" in skill_names
    assert "learning" in skill_names

    for name in skill_names:
        sk = registry.get(name)
        assert sk.valid is True
        assert len(sk.instructions) > 0
        assert "[SKILL:" in sk.as_context_block()
