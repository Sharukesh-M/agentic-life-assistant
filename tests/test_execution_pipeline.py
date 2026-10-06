"""
tests/test_execution_pipeline.py — JARVIS-X Pipeline Integration Tests

Tests end-to-end task creation, database persistence, WorkspaceManager navigation,
and learning workspace content generation.
"""

import json
from pathlib import Path
import pytest

from actions.workspace_actions import handle_workspace_action
from core.workspace_manager import get_workspace_manager, WorkspaceName
from memory.task_store import get_task_store, TaskStatus
from agents.learning_agent import LearningAgent, _load_concepts, _save_concepts, ConceptRecord
from core.learning_renderer import LearningContentRenderer, ContentType


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Isolate tasks and memory stores to a clean temporary directory."""
    test_tasks_path = tmp_path / "tasks.json"
    test_goals_path = tmp_path / "goals.json"
    test_concepts_path = tmp_path / "concepts.json"

    store = get_task_store()
    monkeypatch.setattr(store, "_path", test_tasks_path)

    import agents.goal_agent as ga
    monkeypatch.setattr(ga.GoalAgent, "_GOALS_PATH", test_goals_path)

    import agents.learning_agent as la
    monkeypatch.setattr(la, "_CONCEPTS_PATH", test_concepts_path)

    wm = get_workspace_manager()
    wm.set_active_workspace("HOME")

    yield tmp_path


def test_create_task_end_to_end():
    """Verify task creation mutates database storage and returns success confirmation."""
    res_str = handle_workspace_action({
        "action": "create_task",
        "title": "Revise Python Fundamentals",
        "duration": 45,
        "priority": 1,
    })

    assert "Created task: 'Revise Python Fundamentals'" in res_str

    # Verify task exists in database
    store = get_task_store()
    tasks = store.all()
    assert len(tasks) == 1
    assert tasks[0].title == "Revise Python Fundamentals"
    assert tasks[0].duration_minutes == 45


def test_open_tasks_end_to_end():
    """Verify open_task_workspace changes active_workspace state to TASKS."""
    wm = get_workspace_manager()
    res = wm.open_task_workspace()

    assert res["success"] is True
    assert res["workspace"] == "TASKS"
    assert wm.state.active_workspace == WorkspaceName.TASKS


def test_open_learning_end_to_end():
    """Verify open_learning_workspace changes active_workspace state to LEARNING."""
    wm = get_workspace_manager()
    res = wm.open_learning_workspace()

    assert res["success"] is True
    assert res["workspace"] == "LEARNING"
    assert wm.state.active_workspace == WorkspaceName.LEARNING


def test_get_today_tasks_auto_seeds_and_persists():
    """Verify get_today_tasks auto-seeds tasks from active goals when database is empty."""
    store = get_task_store()
    assert len(store.today()) == 0

    # Seed an active goal
    import agents.goal_agent as ga
    goal_agent = ga.GoalAgent()
    goal_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "Placement Prep"}})

    res_text = handle_workspace_action({"action": "get_today_tasks"})

    assert "Here's your plan for today:" in res_text
    persisted_today = store.today()
    assert len(persisted_today) > 0


def test_learning_content_renderer():
    """Verify LearningContentRenderer generates structured learning components."""
    card = LearningContentRenderer.render_concept_card(
        title="Python Loops",
        definition="Repeats a block of code.",
        key_points=["for loop", "while loop"],
        example="for i in range(5): print(i)",
    )
    assert card.component_type == ContentType.CONCEPT_CARD
    assert card.data["definition"] == "Repeats a block of code."
    assert "for loop" in card.data["key_points"]


def test_learning_agent_personalized_content_generation():
    """Verify LearningAgent generates goal-aware personalized learning content adhering to output contract."""
    agent = LearningAgent()
    res = agent.handle("generate_content", {"tool_args": {"subject": "Placement DSA Arrays", "time_minutes": 45}})

    assert res is not None
    assert "Generated personalized learning session" in res.message
    assert "response" in res.data
    assert "components" in res.data

    response = res.data["response"]
    assert response.get("type") == "LEARNING_RESPONSE"
    assert "goal" in response
    assert "personalization" in response
    assert "learning_objective" in response
    assert "content" in response
    assert "assessment" in response
    assert "next_step" in response
    assert len(res.data["components"]) > 0

    wm = get_workspace_manager()
    assert wm.state.active_workspace == WorkspaceName.LEARNING

