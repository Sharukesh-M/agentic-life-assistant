"""
Database & Repository Unit Tests.
Tests connection, schema initialization, CRUD repositories, and user security isolation.
"""

import sys
import os
import unittest
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_engine, get_session_factory
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.agent_run_repository import AgentRunRepository
from app.db.repositories.notification_repository import NotificationRepository

class TestDatabaseAndRepositories(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use isolated SQLite in-memory database for testing
        cls.config = DBConfig(database_url="sqlite:///:memory:")
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.session = self.SessionFactory()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_user_repository(self):
        repo = UserRepository(self.session)
        user = repo.get_or_create("user_alpha")
        self.assertEqual(user.user_id, "user_alpha")

    def test_goal_and_milestone_repository(self):
        user_repo = UserRepository(self.session)
        user_repo.get_or_create("user_beta")

        goal_repo = GoalRepository(self.session)
        goal = goal_repo.create_goal(
            goal_id="g_101",
            user_id="user_beta",
            title="Learn Rust Programming",
            category="Software Development",
            priority="HIGH"
        )
        self.assertEqual(goal.title, "Learn Rust Programming")

        ms = goal_repo.add_milestone(
            milestone_id="ms_101",
            goal_id="g_101",
            title="Ownership & Borrowing",
            order_index=1
        )
        self.assertEqual(ms.title, "Ownership & Borrowing")

        active_goals = goal_repo.list_active_goals("user_beta")
        self.assertEqual(len(active_goals), 1)

    def test_task_repository_and_honesty_enforcement(self):
        user_repo = UserRepository(self.session)
        user_repo.get_or_create("user_gamma")

        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(goal_id="g_202", user_id="user_gamma", title="Fitness Challenge")

        task_repo = TaskRepository(self.session)
        task = task_repo.create_task(
            task_id="t_202",
            goal_id="g_202",
            user_id="user_gamma",
            title="Run 5km Workout",
            priority="HIGH"
        )
        self.assertEqual(task.status, "CREATED")

        # Honesty Rule Enforcement: Indirect signal must fail to set COMPLETED
        with self.assertRaises(ValueError) as ctx:
            task_repo.update_task_status(
                task_id="t_202",
                user_id="user_gamma",
                new_status="COMPLETED",
                source="git_commit" # Indirect signal!
            )
        self.assertIn("Honesty Rule Violation", str(ctx.exception))

        # Explicit user confirmation must succeed
        updated = task_repo.update_task_status(
            task_id="t_202",
            user_id="user_gamma",
            new_status="COMPLETED",
            source="user_explicit_confirmation"
        )
        self.assertEqual(updated.status, "COMPLETED")
        self.assertEqual(updated.completion_source, "user_explicit_confirmation")

    def test_user_data_security_isolation(self):
        """User A must NEVER be able to retrieve User B's goals or tasks."""
        user_repo = UserRepository(self.session)
        user_repo.get_or_create("user_a")
        user_repo.get_or_create("user_b")

        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(goal_id="g_user_a", user_id="user_a", title="User A Secret Goal")

        user_b_goals = goal_repo.list_active_goals("user_b")
        self.assertEqual(len(user_b_goals), 0)

        # Retrieval by goal_id with wrong user_id must return None
        none_goal = goal_repo.get_goal("g_user_a", user_id="user_b")
        self.assertIsNone(none_goal)

if __name__ == "__main__":
    unittest.main()
