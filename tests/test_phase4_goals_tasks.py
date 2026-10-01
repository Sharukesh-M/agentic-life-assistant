"""
tests/test_phase4_goals_tasks.py - JARVIS-X Phase 4 Goals-Tasks-Progress Loop Tests

Tests deep integration between GoalAgent, PlanningAgent, ProgressAgent, TaskStore,
and goal_tracker plugin.
"""

import json
from pathlib import Path
import pytest

from agents.goal_agent import GoalAgent
from agents.planning_agent import PlanningAgent
from agents.progress_agent import ProgressAgent
from memory.task_store import get_task_store, TaskStatus


@pytest.fixture(autouse=True)
def clean_memory_files(tmp_path, monkeypatch):
    """Isolate tests to temporary goals.json and tasks.json files."""
    test_goals_path = tmp_path / "goals.json"
    test_tasks_path = tmp_path / "tasks.json"

    # Patch paths in agents and stores
    monkeypatch.setattr(GoalAgent, "_GOALS_PATH", test_goals_path)
    monkeypatch.setattr(PlanningAgent, "_GOALS_PATH", test_goals_path)
    monkeypatch.setattr(ProgressAgent, "_GOALS_PATH", test_goals_path)

    import plugins.goal_tracker as gt
    monkeypatch.setattr(gt, "DATA_PATH", test_goals_path)

    import core.goal_workflow as gw
    monkeypatch.setattr(gw, "GOALS_PATH", test_goals_path)
    # Prevent actual browser popups during tests
    monkeypatch.setattr(gw, "_open_chrome_searches", lambda q: True)

    store = get_task_store()
    monkeypatch.setattr(store, "_path", test_tasks_path)

    yield tmp_path


def test_goal_creation_auto_seeds_tasks_and_workflow():
    """Creating a goal via GoalAgent seeds research & tasks into TaskStore."""
    agent = GoalAgent()
    res = agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "Learn Rust"}})
    assert res.success
    assert "Learn Rust" in res.message
    assert res.data.get("created") is True
    assert res.data.get("tasks_seeded") is True

    # Check tasks in TaskStore
    store = get_task_store()
    all_tasks = store.all()
    assert len(all_tasks) > 0
    assert any(t.goal_subject == "Learn Rust" for t in all_tasks)


def test_goal_decomposition():
    """GoalAgent decompose breaks down a goal into milestones and seeds tasks."""
    goal_agent = GoalAgent()
    goal_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "AWS Certification"}})

    res = goal_agent.handle("decompose_goal", {
        "tool_args": {
            "action": "decompose",
            "subject": "AWS Certification",
            "milestones": [
                {"title": "IAM & Security", "tasks": [{"title": "Study IAM Policies"}]},
                {"title": "EC2 & VPC", "tasks": [{"title": "Setup VPC Peering"}]}
            ]
        }
    })

    assert res.success
    assert "Decomposed goal 'AWS Certification'" in res.message
    assert len(res.data["milestones"]) == 2

    store = get_task_store()
    aws_tasks = [t for t in store.all() if t.goal_subject == "AWS Certification"]
    assert len(aws_tasks) >= 2
    titles = [t.title for t in aws_tasks]
    assert "Study IAM Policies" in titles
    assert "Setup VPC Peering" in titles


def test_planning_agent_auto_seeds_and_schedules():
    """PlanningAgent daily plan auto-seeds tasks if missing and builds schedule."""
    goal_agent = GoalAgent()
    goal_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "GATE Exam"}})

    planner = PlanningAgent()
    plan_res = planner.handle("daily_plan", {"tool_args": {"action": "daily_plan"}})

    assert plan_res.success
    assert "Suggested plan for" in plan_res.message
    assert len(plan_res.data["blocks"]) > 0
    assert "GATE Exam" in plan_res.data["goals_addressed"]


def test_progress_agent_completion_and_checkin_sync():
    """Completing a task via ProgressAgent updates TaskStore and syncs checkins."""
    goal_agent = GoalAgent()
    goal_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "Fitness Goal"}})

    store = get_task_store()
    pending = store.pending()
    assert len(pending) > 0
    target_task = pending[0]

    prog_agent = ProgressAgent()
    comp_res = prog_agent.handle("complete_task", {
        "tool_args": {"action": "complete_task", "task_id": target_task.id}
    })

    assert comp_res.success
    assert "Task completed" in comp_res.message

    # Verify task status in store
    updated = store.get(target_task.id)
    assert updated.status == TaskStatus.COMPLETED

    # Verify checkin synced to goal_tracker / goals.json
    import plugins.goal_tracker as gt
    goals = gt._load()
    fg = next(g for g in goals if g["subject"] == "Fitness Goal")
    assert len(fg["checkins"]) > 0
    assert f"Completed task: {target_task.title}" in fg["checkins"][-1]["note"]


def test_progress_agent_skip_pattern_detection():
    """Skipping multiple tasks triggers skip pattern observation."""
    goal_agent = GoalAgent()
    goal_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "Deep Learning"}})

    store = get_task_store()
    goal_agent.handle("decompose_goal", {
        "tool_args": {
            "action": "decompose",
            "subject": "Deep Learning",
            "milestones": [
                {"title": "Math Foundation", "tasks": [
                    {"title": "Linear Algebra Ch 1"},
                    {"title": "Calculus Ch 2"},
                    {"title": "Probability Ch 3"},
                ]}
            ]
        }
    })

    tasks = store.pending()
    prog_agent = ProgressAgent()

    # Skip 3 tasks to trigger skip pattern threshold
    for t in tasks[:3]:
        prog_agent.handle("skip_task", {
            "tool_args": {"action": "skip_task", "task_id": t.id, "reason": "Too tired"}
        })

    # Verify skip pattern in ProgressAgent
    pattern_res = prog_agent.handle("skip_pattern", {"tool_args": {"action": "skip_pattern"}})
    assert pattern_res.success
    assert "Deep Learning" in pattern_res.message

    # Verify weekly review surfaces observations
    review_res = prog_agent.handle("weekly_review", {"tool_args": {"action": "weekly_review"}})
    assert review_res.success
    assert "Observations:" in review_res.message


def test_end_to_end_goals_tasks_progress_loop():
    """Full lifecycle: Create Goal -> Plan -> Execute Tasks -> Report Progress."""
    # 1. Create Goal
    g_agent = GoalAgent()
    g_res = g_agent.handle("create_goal", {"tool_args": {"action": "create", "subject": "Spanish Language"}})
    assert g_res.success

    # 2. Plan
    pl_agent = PlanningAgent()
    pl_res = pl_agent.handle("daily_plan", {"tool_args": {"action": "daily_plan"}})
    assert pl_res.success

    # 3. Complete Task
    pr_agent = ProgressAgent()
    store = get_task_store()
    pending = store.pending()
    assert len(pending) > 0
    done_task = pending[0]

    c_res = pr_agent.handle("complete_task", {
        "tool_args": {"action": "complete_task", "task_id": done_task.id}
    })
    assert c_res.success

    # 4. Report Progress
    rep_res = pr_agent.handle("progress_report", {"tool_args": {"action": "progress_report"}})
    assert rep_res.success
    assert "Progress on 'Spanish Language'" in rep_res.message
    assert "1 of" in rep_res.message
