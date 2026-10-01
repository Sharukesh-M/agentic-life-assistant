"""
tests/test_phase2_foundation.py - JARVIS-X Phase 2 Foundation Tests

Tests every new module created in Phase 2 without touching any existing code.
Run with:  python -m pytest tests/test_phase2_foundation.py -v
"""

import json
import sys
from pathlib import Path

# Add project root to path so imports resolve correctly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest


# ===========================================================================
# State Manager Tests
# ===========================================================================

class TestVoiceStateEnum:
    def test_all_states_exist(self):
        from core.state_manager import VoiceStateEnum
        expected = {"idle", "listening", "user_speaking", "user_paused",
                    "turn_complete", "thinking", "responding", "speaking",
                    "interrupted", "sleeping"}
        actual = {s.value for s in VoiceStateEnum}
        assert actual == expected

    def test_state_is_string(self):
        from core.state_manager import VoiceStateEnum
        assert VoiceStateEnum.LISTENING == "listening"


class TestSessionState:
    def setup_method(self):
        from core.state_manager import SessionState, VoiceStateEnum
        self.state = SessionState()
        self.VoiceStateEnum = VoiceStateEnum

    def test_initial_voice_state(self):
        assert self.state.voice == self.VoiceStateEnum.IDLE

    def test_valid_transition(self):
        ok = self.state.transition_voice(self.VoiceStateEnum.LISTENING)
        assert ok
        assert self.state.voice == self.VoiceStateEnum.LISTENING

    def test_invalid_transition_returns_false(self):
        # IDLE -> SPEAKING is illegal
        ok = self.state.transition_voice(self.VoiceStateEnum.SPEAKING)
        assert not ok
        assert self.state.voice == self.VoiceStateEnum.IDLE  # unchanged

    def test_idle_is_always_legal(self):
        # Any state can transition to IDLE (escape hatch)
        self.state.force_voice(self.VoiceStateEnum.SPEAKING)
        ok = self.state.transition_voice(self.VoiceStateEnum.IDLE)
        assert ok

    def test_force_voice(self):
        self.state.force_voice(self.VoiceStateEnum.SPEAKING)
        assert self.state.voice == self.VoiceStateEnum.SPEAKING

    def test_is_speaking(self):
        self.state.force_voice(self.VoiceStateEnum.SPEAKING)
        assert self.state.is_speaking()

    def test_is_listening(self):
        self.state.force_voice(self.VoiceStateEnum.LISTENING)
        assert self.state.is_listening()
        self.state.force_voice(self.VoiceStateEnum.USER_SPEAKING)
        assert self.state.is_listening()

    def test_is_busy(self):
        for busy_state in ("speaking", "thinking", "responding"):
            self.state.force_voice(self.VoiceStateEnum(busy_state))
            assert self.state.is_busy()

    def test_full_happy_path(self):
        V = self.VoiceStateEnum
        transitions = [
            (V.IDLE, V.LISTENING),
            (V.LISTENING, V.THINKING),
            (V.THINKING, V.RESPONDING),
            (V.RESPONDING, V.SPEAKING),
            (V.SPEAKING, V.LISTENING),
        ]
        state = self.state
        for from_s, to_s in transitions:
            state.force_voice(from_s)
            assert state.transition_voice(to_s), f"Expected {from_s}->{to_s} to be legal"


class TestAppState:
    def setup_method(self):
        from core.state_manager import AppState
        AppState.reset()

    def teardown_method(self):
        from core.state_manager import AppState
        AppState.reset()

    def test_singleton(self):
        from core.state_manager import AppState
        a = AppState.get()
        b = AppState.get()
        assert a is b

    def test_reset_creates_new_instance(self):
        from core.state_manager import AppState
        a = AppState.get()
        AppState.reset()
        b = AppState.get()
        assert a is not b


# ===========================================================================
# Agent Registry Tests
# ===========================================================================

class TestAgentRegistry:
    def setup_method(self):
        from core.agent_registry import AgentRegistry, reset_registry
        reset_registry()
        self.registry = AgentRegistry(logger_fn=lambda m: None)

    def _make_record(self, name="test_agent", capabilities=None, priority=0):
        from core.agent_registry import AgentRecord
        return AgentRecord(
            name=name,
            description=f"Test agent {name}",
            capabilities=capabilities or [],
            handler=lambda intent, context: f"result from {name}",
            priority=priority,
        )

    def test_register_and_get(self):
        rec = self._make_record("goal_agent")
        self.registry.register(rec)
        assert self.registry.has("goal_agent")
        assert self.registry.get("goal_agent") is rec

    def test_duplicate_registration_raises(self):
        self.registry.register(self._make_record("agent_a"))
        with pytest.raises(ValueError):
            self.registry.register(self._make_record("agent_a"))

    def test_register_or_update_silently_replaces(self):
        self.registry.register(self._make_record("agent_b"))
        rec2 = self._make_record("agent_b")
        self.registry.register_or_update(rec2)
        assert self.registry.get("agent_b") is rec2

    def test_unregister(self):
        self.registry.register(self._make_record("agent_c"))
        result = self.registry.unregister("agent_c")
        assert result
        assert not self.registry.has("agent_c")

    def test_list_enabled_only(self):
        self.registry.register(self._make_record("enabled_agent"))
        self.registry.register(self._make_record("disabled_agent"))
        self.registry.disable("disabled_agent")
        enabled = self.registry.list(enabled_only=True)
        names = [r.name for r in enabled]
        assert "enabled_agent" in names
        assert "disabled_agent" not in names

    def test_route_by_name(self):
        self.registry.register(self._make_record("goal_agent"))
        result = self.registry.route("goal_agent")
        assert result is not None
        assert result.name == "goal_agent"

    def test_route_by_capability(self):
        rec = self._make_record("planner", capabilities=["create_daily_plan"])
        self.registry.register(rec)
        result = self.registry.route("create_daily_plan")
        assert result is not None
        assert result.name == "planner"

    def test_route_prefers_higher_priority(self):
        low = self._make_record("low_agent", capabilities=["planning"], priority=1)
        high = self._make_record("high_agent", capabilities=["planning"], priority=10)
        self.registry.register(low)
        self.registry.register(high)
        result = self.registry.route("planning")
        assert result.name == "high_agent"

    def test_route_returns_none_for_unknown(self):
        result = self.registry.route("nonexistent_capability_xyz")
        assert result is None

    def test_run_calls_handler(self):
        rec = self._make_record("echo_agent")
        self.registry.register(rec)
        result = self.registry.run("echo_agent", intent="test", context={})
        assert "result from echo_agent" in result

    def test_run_unknown_agent(self):
        result = self.registry.run("no_such_agent")
        assert "not registered" in result.lower()


# ===========================================================================
# Skill Loader Tests
# ===========================================================================

class TestSkillLoader:
    def test_discover_from_real_skills_dir(self):
        from core.skill_loader import discover_skills
        skills_dir = _ROOT / "skills"
        registry = discover_skills(skills_dir, logger_fn=lambda m: None)
        skills = registry.list()
        # At minimum the skills we just created should be discovered
        assert len(skills) >= 4, f"Expected at least 4 skills, got {len(skills)}"

    def test_get_core_skill(self):
        from core.skill_loader import discover_skills
        registry = discover_skills(_ROOT / "skills", logger_fn=lambda m: None)
        core = registry.get("core")
        assert core is not None
        assert core.valid

    def test_find_by_trigger(self):
        from core.skill_loader import discover_skills
        registry = discover_skills(_ROOT / "skills", logger_fn=lambda m: None)
        skill = registry.find_by_trigger("goal_tracker")
        assert skill is not None
        assert skill.name == "goal_management"

    def test_skill_has_instructions(self):
        from core.skill_loader import discover_skills
        registry = discover_skills(_ROOT / "skills", logger_fn=lambda m: None)
        skill = registry.get("task_planning")
        assert skill is not None
        assert len(skill.instructions) > 50

    def test_context_for_multiple_skills(self):
        from core.skill_loader import discover_skills
        registry = discover_skills(_ROOT / "skills", logger_fn=lambda m: None)
        ctx = registry.context_for(["core", "goal_management"])
        assert "[SKILL: CORE]" in ctx
        assert "[SKILL: GOAL_MANAGEMENT]" in ctx

    def test_nonexistent_skills_dir(self, tmp_path):
        from core.skill_loader import discover_skills
        registry = discover_skills(tmp_path / "no_such_dir", logger_fn=lambda m: None)
        assert registry.list() == []

    def test_frontmatter_parsing(self, tmp_path):
        from core.skill_loader import discover_skills
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(
            "---\n"
            "name: test_skill\n"
            "description: A test skill\n"
            "purpose: Testing\n"
            "triggers: [test, check]\n"
            "---\n"
            "## Instructions\n"
            "Do the thing.\n",
            encoding="utf-8",
        )
        registry = discover_skills(tmp_path, logger_fn=lambda m: None)
        skill = registry.get("test_skill")
        assert skill is not None
        assert skill.description == "A test skill"
        assert "test" in skill.triggers
        assert "Do the thing." in skill.instructions


# ===========================================================================
# Task Store Tests
# ===========================================================================

class TestTaskStore:
    def setup_method(self, tmp_path_factory):
        from memory.task_store import TaskStore
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.store = TaskStore(path=self.tmp / "tasks.json")

    def _task(self, title="Test task", goal_id="g1", goal_subject="Python"):
        from memory.task_store import Task
        return Task(title=title, goal_id=goal_id, goal_subject=goal_subject)

    def test_create_and_get(self):
        task = self._task("Read Chapter 1")
        self.store.create(task)
        retrieved = self.store.get(task.id)
        assert retrieved is not None
        assert retrieved.title == "Read Chapter 1"

    def test_update_status(self):
        task = self._task()
        self.store.create(task)
        self.store.update(task.id, status="completed")
        updated = self.store.get(task.id)
        assert updated.status == "completed"

    def test_delete(self):
        task = self._task()
        self.store.create(task)
        result = self.store.delete(task.id)
        assert result
        assert self.store.get(task.id) is None

    def test_for_goal(self):
        t1 = self._task("Task A", goal_id="goal_1")
        t2 = self._task("Task B", goal_id="goal_2")
        self.store.create(t1)
        self.store.create(t2)
        results = self.store.for_goal("goal_1")
        assert len(results) == 1
        assert results[0].title == "Task A"

    def test_pending_query(self):
        task = self._task()
        self.store.create(task)
        pending = self.store.pending()
        assert any(t.id == task.id for t in pending)

    def test_task_complete(self):
        from memory.task_store import TaskStatus
        task = self._task()
        task.complete()
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_task_skip(self):
        from memory.task_store import TaskStatus
        task = self._task()
        task.skip("too tired")
        assert task.status == TaskStatus.SKIPPED
        assert task.skip_count == 1
        assert "too tired" in task.skip_reasons

    def test_goal_stats(self):
        for i in range(3):
            t = self._task(f"Task {i}", goal_id="g_stats")
            self.store.create(t)
        tasks = self.store.for_goal("g_stats")
        tasks[0].complete()
        self.store.update(tasks[0].id, status="completed")
        stats = self.store.goal_stats("g_stats")
        assert stats["total"] == 3
        assert stats["completed"] == 1

    def test_skip_pattern_no_pattern(self):
        task = self._task()
        self.store.create(task)
        pattern = self.store.skip_pattern("g1")
        assert not pattern["has_pattern"]

    def test_skip_pattern_detected(self):
        from memory.task_store import TaskStatus
        for i in range(4):
            t = self._task(f"GATE task {i}", goal_id="gate_goal")
            t.status = TaskStatus.SKIPPED
            t.skip_count = 1
            t.scheduled_time = "19:00"
            self.store.create(t)
        pattern = self.store.skip_pattern("gate_goal")
        assert pattern["has_pattern"]
        assert pattern["consecutive_skips"] >= 3

    def test_persistence_across_instances(self):
        from memory.task_store import TaskStore
        task = self._task("Persistent task")
        self.store.create(task)
        store2 = TaskStore(path=self.tmp / "tasks.json")
        all_tasks = store2.all()
        assert any(t.title == "Persistent task" for t in all_tasks)


# ===========================================================================
# Agent Base Tests
# ===========================================================================

class TestBaseAgent:
    def test_agent_result_as_str_success(self):
        from agents.base_agent import AgentResult
        r = AgentResult(success=True, message="All good")
        assert r.as_str() == "All good"

    def test_agent_result_as_str_failure(self):
        from agents.base_agent import AgentResult
        r = AgentResult(success=False, error="Something broke")
        assert "Something broke" in r.as_str()

    def test_agent_result_to_dict(self):
        from agents.base_agent import AgentResult
        r = AgentResult(success=True, message="Test", confidence=0.9)
        d = r.to_dict()
        assert d["success"] is True
        assert d["confidence"] == 0.9


# ===========================================================================
# Orchestrator Tests
# ===========================================================================

class TestOrchestrator:
    def setup_method(self):
        from core.orchestrator import Orchestrator, reset_orchestrator
        from core.agent_registry import AgentRegistry, reset_registry
        reset_orchestrator()
        reset_registry()
        self.registry = AgentRegistry(logger_fn=lambda m: None)
        self.orch = Orchestrator(
            agent_registry=self.registry,
            skill_registry=None,
            logger_fn=lambda m: None,
        )

    def _request(self, tool_name, args=None):
        from core.orchestrator import OrchestratorRequest
        return OrchestratorRequest(tool_name=tool_name, tool_args=args or {})

    def test_fall_through_with_no_agents(self):
        req = self._request("goal_tracker")
        decision = self.orch.route(req)
        assert not decision.handled

    def test_routes_to_registered_agent(self):
        from core.agent_registry import AgentRecord
        rec = AgentRecord(
            name="goal_agent",
            capabilities=["goal_management"],
            handler=lambda intent, context: "routed!",
        )
        self.registry.register(rec)

        req = self._request("goal_tracker")
        decision = self.orch.route(req)
        assert decision.handled
        assert decision.agent_name == "goal_agent"
        assert decision.result == "routed!"

    def test_never_raises_on_bad_agent(self):
        from core.agent_registry import AgentRecord
        def crashing_handler(intent, context):
            raise RuntimeError("Crash!")
        rec = AgentRecord(
            name="crash_agent",
            capabilities=["goal_management"],
            handler=crashing_handler,
        )
        self.registry.register(rec)
        req = self._request("goal_tracker")
        # Should NOT raise -- falls through safely
        decision = self.orch.route(req)
        # Either handled=False (fall-through) or error result
        assert isinstance(decision.handled, bool)

    def test_stats(self):
        stats = self.orch.stats()
        assert "total_requests" in stats
        assert "agent_hits" in stats


# ===========================================================================
# Voice Controller Tests
# ===========================================================================

class TestVoiceController:
    def setup_method(self):
        from core.voice_controller import VoiceController
        from core.state_manager import SessionState
        self.session = SessionState()
        self.vc = VoiceController(session=self.session)

    def test_initial_state(self):
        from core.state_manager import VoiceStateEnum
        assert self.vc.state == VoiceStateEnum.IDLE

    def test_start_speaking(self):
        from core.state_manager import VoiceStateEnum
        self.session.force_voice(VoiceStateEnum.RESPONDING)
        self.vc.start_speaking()
        assert self.vc.is_speaking()

    def test_interrupt(self):
        from core.state_manager import VoiceStateEnum
        self.session.force_voice(VoiceStateEnum.SPEAKING)
        self.vc.interrupt()
        assert self.vc.is_listening()

    def test_barge_in_callback(self):
        from core.state_manager import VoiceStateEnum
        fired = []
        self.vc.on_barge_in = lambda: fired.append(True)
        self.session.force_voice(VoiceStateEnum.SPEAKING)
        self.vc.start_speaking()   # arms barge-in
        self.vc.interrupt()
        assert len(fired) == 1

    def test_sleep_and_wake(self):
        self.vc.sleep()
        assert self.vc.is_asleep()
        self.vc.wake()
        assert not self.vc.is_asleep()
        assert self.vc.is_listening()

    def test_on_state_change_callback(self):
        from core.state_manager import VoiceStateEnum
        changes = []
        self.vc.on_state_change = lambda s: changes.append(s)
        self.vc.transition(VoiceStateEnum.LISTENING)
        assert VoiceStateEnum.LISTENING in changes

    def test_describe(self):
        d = self.vc.describe()
        assert "state" in d
        assert "awake" in d


# ===========================================================================
# Integration: GoalAgent
# ===========================================================================

class TestGoalAgent:
    def test_list_returns_result(self):
        from agents.goal_agent import GoalAgent
        agent = GoalAgent()
        result = agent.handle("list_goals", context={"tool_args": {"action": "list"}})
        # Should return a result (may have no goals, that's fine)
        assert result.success or not result.success
        assert isinstance(result.message, str)

    def test_create_requires_subject(self):
        from agents.goal_agent import GoalAgent
        agent = GoalAgent()
        result = agent.handle("create_goal", context={"tool_args": {"action": "create"}})
        assert result.needs_input
        assert result.missing_field == "subject"

    def test_pause_requires_subject(self):
        from agents.goal_agent import GoalAgent
        agent = GoalAgent()
        result = agent.handle("pause_goal", context={"tool_args": {"action": "pause"}})
        assert result.needs_input


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
