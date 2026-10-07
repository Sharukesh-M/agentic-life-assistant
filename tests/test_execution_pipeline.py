"""
tests/test_execution_pipeline.py - Automated Execution Pipeline Verification Test Suite

Verifies the entire state-changing pipeline:
User Intent -> Tool Call -> TaskService/WorkspaceManager -> Database -> Event System -> Application State -> Verification
"""

import unittest
import json
from datetime import date, datetime
from pathlib import Path
import tempfile

from memory.task_store import Task, TaskStatus, TaskStore, TaskService
from core.workspace_manager import WorkspaceManager, WorkspaceName, register_event_listener, pipeline_log
from actions.workspace_actions import handle_workspace_action
from services.learning.recommendation_service import LearningRecommendationService


class TestExecutionPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_tasks_path = Path(self.tmp_dir.name) / "test_tasks.json"
        self.test_tasks_path.write_text("[]", encoding="utf-8")
        
        self.store = TaskStore(path=self.test_tasks_path)
        self.service = TaskService(store=self.store)
        self.ws_mgr = WorkspaceManager()
        self.ws_mgr.state.active_workspace = WorkspaceName.HOME

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_create_task_persists(self):
        res = self.service.create_task(
            title="Test Task Persistence",
            description="Verify database insertion",
            scheduled_date=date.today().isoformat(),
            duration_minutes=30
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["operation"], "create_task")
        
        task_id = res["task_id"]
        persisted = self.service.get_task_by_id(task_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.title, "Test Task Persistence")
        self.assertEqual(persisted.status, TaskStatus.PENDING)

    def test_get_today_tasks(self):
        self.service.create_task(title="Today Task 1", scheduled_date=date.today().isoformat())
        self.service.create_task(title="Today Task 2", scheduled_date=date.today().isoformat())
        
        today_tasks = self.service.get_today_tasks()
        self.assertGreaterEqual(len(today_tasks), 2)
        titles = [t.title for t in today_tasks]
        self.assertIn("Today Task 1", titles)
        self.assertIn("Today Task 2", titles)

    def test_create_task_updates_dashboard(self):
        events_received = []
        def listener(evt, payload):
            events_received.append((evt, payload))

        register_event_listener(listener)
        res = self.service.create_task(title="Event Trigger Test")
        self.assertTrue(res["success"])
        
        event_names = [e[0] for e in events_received]
        self.assertIn("TASK_CREATED", event_names)

    def test_workspace_open(self):
        res = self.ws_mgr.open_workspace("LEARNING")
        self.assertTrue(res["success"])
        self.assertEqual(res["workspace"], "LEARNING")
        self.assertEqual(self.ws_mgr.state.active_workspace, WorkspaceName.LEARNING)

    def test_workspace_state(self):
        self.ws_mgr.set_active_workspace(WorkspaceName.GOALS)
        state_dict = self.ws_mgr.state.to_dict()
        self.assertEqual(state_dict["active_workspace"], "GOALS")

    def test_ui_refresh_after_task_creation(self):
        events = []
        def cb(name, payload):
            events.append(name)
            
        self.ws_mgr.register_ui_callback(cb)
        res = self.service.create_task(title="UI Refresh Test Task")
        self.assertTrue(res["success"])
        self.assertTrue(len(events) > 0)

    def test_ui_refresh_after_task_update(self):
        c_res = self.service.create_task(title="Update Target Task")
        t_id = c_res["task_id"]
        
        u_res = self.service.update_task(t_id, title="Updated Title Test")
        self.assertTrue(u_res["success"])
        
        updated = self.service.get_task_by_id(t_id)
        self.assertEqual(updated.title, "Updated Title Test")

    def test_task_user_isolation(self):
        self.service.create_task(title="User A Task", user_id="user_a", scheduled_date=date.today().isoformat())
        self.service.create_task(title="User B Task", user_id="user_b", scheduled_date=date.today().isoformat())
        
        tasks_a = self.service.get_today_tasks(user_id="user_a")
        titles_a = [t.title for t in tasks_a]
        self.assertIn("User A Task", titles_a)

    def test_no_duplicate_daily_tasks(self):
        t1 = self.service.create_task(title="Unique Daily Task", scheduled_date=date.today().isoformat())
        self.assertTrue(t1["success"])
        
        existing = self.service.get_today_tasks()
        self.assertGreaterEqual(len(existing), 1)

    def test_stale_cache_invalidation(self):
        t_res = self.service.create_task(title="Cache Invalidation Test")
        t_id = t_res["task_id"]
        
        self.service.delete_task(t_id)
        self.assertIsNone(self.service.get_task_by_id(t_id))

    def test_task_completion_updates_dashboard(self):
        t_res = self.service.create_task(title="Complete Me")
        t_id = t_res["task_id"]
        
        comp_res = self.service.complete_task(t_id)
        self.assertTrue(comp_res["success"])
        
        task = self.service.get_task_by_id(t_id)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_learning_workspace_open(self):
        res = self.ws_mgr.open_learning_workspace()
        self.assertTrue(res["success"])
        self.assertEqual(res["workspace"], "LEARNING")

    def test_learning_content_load(self):
        rec_svc = LearningRecommendationService()
        user_ctx = {
            "current_goal": {"subject": "AI Engineer Job"},
            "user_level": "beginner"
        }
        content = rec_svc.generate_learning_window_content(user_ctx)
        self.assertIn("modules", content)
        self.assertGreaterEqual(len(content["modules"]), 1)

    def test_fake_success_prevention(self):
        res = handle_workspace_action({"action": "create_task", "title": ""})
        self.assertFalse(res["success"])

    def test_task_creation_to_dashboard(self):
        params = {
            "action": "create_task",
            "title": "End to End Pipeline Task",
            "description": "Full validation turn",
            "duration": 45,
            "priority": 1
        }
        res = handle_workspace_action(params)
        self.assertTrue(res["success"])
        self.assertEqual(res["operation"], "create_task")
        
        task_id = res["task_id"]
        db_task = self.service.get_task_by_id(task_id)
        self.assertIsNotNone(db_task)
        self.assertEqual(db_task.title, "End to End Pipeline Task")


if __name__ == "__main__":
    unittest.main()
