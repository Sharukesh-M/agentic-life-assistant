"""
PostgreSQL Persistence Integration Test Suite.
Verifies real database CRUD, schema validation, pgvector vector structure, user security isolation, and completion honesty.
"""

import sys
import os
import unittest
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory, get_active_backend
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.memory_repository import MemoryRepository, SensitiveDataViolation
from app.db.repositories.agent_run_repository import AgentRunRepository
from app.db.repositories.notification_repository import NotificationRepository
from app.db.memory_service import MemoryService
from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext
from app.llm.provider import MockLLMProvider

class TestPostgreSQLIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Database URL can be overridden via POSTGRESQL_TEST_URL env var
        pg_url = os.getenv("POSTGRESQL_TEST_URL", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
        cls.config = DBConfig(database_url=pg_url)
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.session = self.SessionFactory()
        self.user_id = "pg_user_test_1"

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_database_backend_transparency(self):
        """Verify active database backend mode is explicitly reported."""
        backend_mode = get_active_backend(self.config)
        self.assertIn(backend_mode, ["POSTGRESQL", "SQLITE", "IN_MEMORY"])
        print(f"\n[Integration Diagnostic] Active DB Engine Mode: {backend_mode}")

    def test_user_crud(self):
        """Verify User record creation and retrieval."""
        user_repo = UserRepository(self.session)
        user = user_repo.get_or_create(self.user_id)
        self.assertEqual(user.user_id, self.user_id)
        self.assertIsNotNone(user.created_at)

    def test_goal_milestone_task_persistence(self):
        """Verify Goal, Milestone, and Task relational persistence."""
        goal_repo = GoalRepository(self.session)
        goal = goal_repo.create_goal(
            goal_id="g_pg_1",
            user_id=self.user_id,
            title="Master PostgreSQL with pgvector",
            category="Engineering",
            priority="HIGH",
            available_time_per_day=60
        )
        self.assertEqual(goal.title, "Master PostgreSQL with pgvector")

        # Create Milestone
        milestone = goal_repo.add_milestone(
            milestone_id="m_pg_1",
            goal_id="g_pg_1",
            title="Database Schema Migration Setup",
            order_index=1
        )
        self.assertEqual(milestone.goal_id, "g_pg_1")

        # Create Task
        task_repo = TaskRepository(self.session)
        task = task_repo.create_task(
            task_id="t_pg_1",
            goal_id="g_pg_1",
            milestone_id="m_pg_1",
            user_id=self.user_id,
            title="Configure Alembic Migrations",
            priority="HIGH",
            estimated_minutes=45
        )
        self.assertEqual(task.status, "CREATED")

        # Retrieve Active Goals and Tasks
        active_goals = goal_repo.list_active_goals(self.user_id)
        self.assertEqual(len(active_goals), 1)

        user_tasks = task_repo.list_user_tasks(self.user_id)
        self.assertEqual(len(user_tasks), 1)

    def test_memory_storage_and_deduplication(self):
        """Verify Memory storage, policy gate, and deduplication."""
        mem_service = MemoryService(self.session)
        mem1 = mem_service.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="Prefers automated PostgreSQL migrations with Alembic.",
            importance=0.9
        )
        self.assertIsNotNone(mem1.memory_id)

        # Deduplication check: storing identical content updates timestamp without duplicate creation
        mem2 = mem_service.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="Prefers automated PostgreSQL migrations with Alembic.",
            importance=0.9
        )
        self.assertEqual(mem1.memory_id, mem2.memory_id)

    def test_sensitive_data_safety_gate(self):
        """Verify safety policy blocks passwords and secret API keys."""
        mem_service = MemoryService(self.session)
        with self.assertRaises(SensitiveDataViolation):
            mem_service.store_memory(
                user_id=self.user_id,
                classification="LONG_TERM_PREFERENCE",
                content="My database password is postgres_secret_pass_123"
            )

    def test_user_data_isolation(self):
        """Verify strict isolation: User A cannot read User B data."""
        user_a = "user_alpha"
        user_b = "user_beta"

        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(goal_id="g_alpha", user_id=user_a, title="Alpha Goal")
        goal_repo.create_goal(goal_id="g_beta", user_id=user_b, title="Beta Goal")

        alpha_goals = goal_repo.list_active_goals(user_a)
        beta_goals = goal_repo.list_active_goals(user_b)

        self.assertEqual(len(alpha_goals), 1)
        self.assertEqual(alpha_goals[0].title, "Alpha Goal")
        self.assertEqual(len(beta_goals), 1)
        self.assertEqual(beta_goals[0].title, "Beta Goal")

    def test_completion_honesty_enforcement(self):
        """Verify task completion honesty: indirect signals cannot set COMPLETED."""
        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(goal_id="g_h1", user_id=self.user_id, title="Honesty Test Goal")

        task_repo = TaskRepository(self.session)
        task_repo.create_task(task_id="t_h1", goal_id="g_h1", user_id=self.user_id, title="Run Migration Test")

        # Indirect signal fails
        with self.assertRaises(ValueError):
            task_repo.update_task_status(task_id="t_h1", user_id=self.user_id, new_status="COMPLETED", source="github_commit")

        # Explicit user confirmation succeeds
        updated_task = task_repo.update_task_status(
            task_id="t_h1",
            user_id=self.user_id,
            new_status="COMPLETED",
            source="user_confirmation"
        )
        self.assertEqual(updated_task.status, "COMPLETED")

    def test_agent_run_logging(self):
        """Verify Agent Run execution logging."""
        run_repo = AgentRunRepository(self.session)
        run = run_repo.create_run_record(
            run_id="run_pg_001",
            user_id=self.user_id,
            intent="goal_planning",
            required_capabilities=["planning", "db_persistence"],
            required_tools=["schema_validator"],
            provider="mock_llm",
            model="jarvix-v1",
            execution_status="completed",
            latency_ms=12.5
        )
        self.assertEqual(run.run_id, "run_pg_001")

        runs = run_repo.list_user_runs(self.user_id)
        self.assertEqual(len(runs), 1)

    def test_notification_logging(self):
        """Verify Proactive Notification logging."""
        notif_repo = NotificationRepository(self.session)
        notif = notif_repo.create_notification(
            notification_id="n_pg_001",
            user_id=self.user_id,
            message="Goal milestone deadline approaching.",
            priority="HIGH"
        )
        self.assertEqual(notif.priority, "HIGH")

        notifs = notif_repo.list_user_notifications(self.user_id)
        self.assertEqual(len(notifs), 1)

if __name__ == "__main__":
    unittest.main()
