"""
End-to-End Stateful Pipeline Integration Test.
Verifies multi-turn state persistence, DB goal retrieval, memory personalization, and task completion honesty.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory
from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext
from app.db.memory_service import MemoryService
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository
from app.llm.provider import MockLLMProvider

class TestStatefulPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DBConfig(database_url="sqlite:///:memory:")
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.session = self.SessionFactory()
        self.mock_provider = MockLLMProvider()
        self.orchestrator = JARVIXOrchestrator(llm_provider=self.mock_provider)
        self.user_id = "stateful_user_1"

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_stateful_goal_and_task_pipeline(self):
        """
        Turn 1: User creates a 30-day goal plan. System validates plan and persists Goal, Milestones, and Tasks to DB.
        Turn 2: User asks 'What should I do today?'. System loads persisted DB state rather than re-deriving from scratch.
        """
        # Turn 1: Planning Request
        req1 = "I want to learn Generative AI in 30 days."
        ctx1 = AgentContext.load_from_db(user_id=self.user_id, query=req1, session=self.session)
        res1 = self.orchestrator.execute_pipeline(req1, context=ctx1, db_session=self.session)

        self.assertEqual(res1["status"], "completed")
        self.assertEqual(res1["intent"], "goal_planning")
        self.assertTrue(res1["result"]["success"])

        # Verify Goal and Tasks were persisted to DB
        goal_repo = GoalRepository(self.session)
        active_goals = goal_repo.list_active_goals(self.user_id)
        self.assertEqual(len(active_goals), 1)
        self.assertIn("Generative AI", active_goals[0].title)

        task_repo = TaskRepository(self.session)
        user_tasks = task_repo.list_user_tasks(self.user_id)
        self.assertGreater(len(user_tasks), 0)

        # Turn 2: Query Active Progress
        req2 = "What should I do today?"
        ctx2 = AgentContext.load_from_db(user_id=self.user_id, query=req2, session=self.session)
        self.assertEqual(len(ctx2.active_goals), 1)
        self.assertGreater(len(ctx2.existing_tasks), 0)

        res2 = self.orchestrator.execute_pipeline(req2, context=ctx2, db_session=self.session)
        self.assertEqual(res2["status"], "completed")

    def test_memory_personalization_pipeline(self):
        """
        User states a learning preference. Memory Service persists it to DB.
        Later request retrieves preference and injects it into AgentContext.
        """
        mem_service = MemoryService(self.session)
        mem_service.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="User learns best from worked PyTorch code examples."
        )

        query = "Explain transformers."
        ctx = AgentContext.load_from_db(user_id=self.user_id, query=query, session=self.session)
        self.assertEqual(len(ctx.retrieved_memories), 1)
        self.assertIn("PyTorch code examples", ctx.retrieved_memories[0])

    def test_completion_honesty_policy(self):
        """Indirect signal must NOT set task COMPLETED."""
        goal_repo = GoalRepository(self.session)
        goal = goal_repo.create_goal(goal_id="g_honesty", user_id=self.user_id, title="Train CNN Model")

        task_repo = TaskRepository(self.session)
        task = task_repo.create_task(task_id="t_honesty", goal_id="g_honesty", user_id=self.user_id, title="Execute Epoch 10")

        # Indirect signal fails
        with self.assertRaises(ValueError):
            task_repo.update_task_status(task_id="t_honesty", user_id=self.user_id, new_status="COMPLETED", source="github_commit")

        # Task remains CREATED
        fresh_task = task_repo.get_task("t_honesty", self.user_id)
        self.assertEqual(fresh_task.status, "CREATED")

if __name__ == "__main__":
    unittest.main()
