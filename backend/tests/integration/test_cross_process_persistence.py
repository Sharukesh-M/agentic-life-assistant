"""
Cross-Process / Cross-Session Persistence Integration Test Suite.
Verifies memory preference persistence across fresh session boundaries, preference contradiction resolution, and multi-turn state retrieval.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory
from app.db.memory_service import MemoryService
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository
from app.agent.agent_context import AgentContext
from app.agent.orchestrator import JARVIXOrchestrator
from app.llm.provider import MockLLMProvider

class TestCrossProcessPersistence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pg_url = os.getenv("POSTGRESQL_TEST_URL", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
        cls.config = DBConfig(database_url=pg_url)
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.user_id = "cross_session_user_99"

    def test_cross_session_memory_retrieval(self):
        """
        Process/Session 1: User states preference -> Persisted to DB -> Session 1 closes.
        Process/Session 2: Fresh session opens -> User asks query -> Preference retrieved into AgentContext.
        """
        # Session 1: Write User Preference
        session1 = self.SessionFactory()
        mem_service1 = MemoryService(session1)
        mem_service1.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="User learns best from worked PyTorch code examples."
        )
        session1.close() # Simulate process 1 ending

        # Session 2: Read in Fresh Process/Session
        session2 = self.SessionFactory()
        ctx2 = AgentContext.load_from_db(user_id=self.user_id, query="Explain transformers.", session=session2)
        
        self.assertEqual(len(ctx2.retrieved_memories), 1)
        self.assertIn("PyTorch code examples", ctx2.retrieved_memories[0])
        session2.close()

    def test_preference_contradiction_resolution(self):
        """
        Session 1: Persist 'Prefers evening study sessions.'
        Session 2: Persist 'I prefer studying in the morning now.'
        Session 3: Verify old preference is deactivated/superseded and only new preference is retrieved.
        """
        # Session 1: Initial Preference
        session1 = self.SessionFactory()
        mem_service1 = MemoryService(session1)
        mem1 = mem_service1.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="Prefers evening study sessions."
        )
        session1.close()

        # Session 2: Updated Contradictory Preference
        session2 = self.SessionFactory()
        mem_service2 = MemoryService(session2)
        mem2 = mem_service2.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="I prefer studying in the morning now."
        )
        session2.close()

        # Session 3: Query Active Memories
        session3 = self.SessionFactory()
        mem_service3 = MemoryService(session3)
        active_memories = mem_service3.list_active_memories(self.user_id)

        # Only 1 active memory must exist
        self.assertEqual(len(active_memories), 1)
        self.assertIn("morning", active_memories[0].content.lower())
        session3.close()

    def test_multi_turn_stateful_goal_retrieval(self):
        """
        Turn 1: Orchestrator executes planning -> Persists goal & tasks -> Session 1 closes.
        Turn 2: Fresh Session 2 loads user context -> Active goals & tasks loaded directly from DB.
        """
        mock_provider = MockLLMProvider()
        orchestrator = JARVIXOrchestrator(llm_provider=mock_provider)

        # Turn 1: Create Plan
        session1 = self.SessionFactory()
        req1 = "I want to learn Generative AI in 30 days."
        ctx1 = AgentContext.load_from_db(user_id=self.user_id, query=req1, session=session1)
        res1 = orchestrator.execute_pipeline(req1, context=ctx1, db_session=session1)
        self.assertEqual(res1["status"], "completed")
        session1.close()

        # Turn 2: Fresh Query
        session2 = self.SessionFactory()
        req2 = "What should I work on today?"
        ctx2 = AgentContext.load_from_db(user_id=self.user_id, query=req2, session=session2)
        
        self.assertEqual(len(ctx2.active_goals), 1)
        self.assertGreater(len(ctx2.existing_tasks), 0)
        self.assertIn("Generative AI", ctx2.active_goals[0]["title"])
        
        res2 = orchestrator.execute_pipeline(req2, context=ctx2, db_session=session2)
        self.assertEqual(res2["status"], "completed")
        session2.close()

if __name__ == "__main__":
    unittest.main()
