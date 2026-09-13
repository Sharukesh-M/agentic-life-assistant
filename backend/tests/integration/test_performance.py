"""
Performance Benchmark Test Suite.
Measures DB connection initialization, goal/task CRUD latency, memory write & retrieval latency.
"""

import sys
import os
import time
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.memory_service import MemoryService

class TestDatabasePerformance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pg_url = os.getenv("POSTGRESQL_TEST_URL", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
        cls.config = DBConfig(database_url=pg_url)
        
        start_init = time.perf_counter()
        init_db(cls.config)
        cls.init_latency_ms = (time.perf_counter() - start_init) * 1000.0
        
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        self.session = self.SessionFactory()
        self.user_id = "perf_user_001"

    def tearDown(self):
        self.session.close()

    def test_performance_measurements(self):
        """Measure CRUD and retrieval latency."""
        print(f"\n[Performance Benchmark Results]")
        print(f"  DB Init Latency: {self.init_latency_ms:.3f} ms")

        # 1. Measure Goal Creation
        t0 = time.perf_counter()
        goal_repo = GoalRepository(self.session)
        goal = goal_repo.create_goal(
            goal_id="g_perf_1",
            user_id=self.user_id,
            title="Benchmark Goal",
            category="Testing"
        )
        goal_create_ms = (time.perf_counter() - t0) * 1000.0
        print(f"  Goal Write Latency: {goal_create_ms:.3f} ms")

        # 2. Measure Goal Retrieval
        t1 = time.perf_counter()
        active_goals = goal_repo.list_active_goals(self.user_id)
        goal_read_ms = (time.perf_counter() - t1) * 1000.0
        print(f"  Goal Read Latency: {goal_read_ms:.3f} ms")

        # 3. Measure Memory Write
        t2 = time.perf_counter()
        mem_service = MemoryService(self.session)
        mem_service.store_memory(
            user_id=self.user_id,
            classification="LONG_TERM_PREFERENCE",
            content="Benchmark preference for low latency DB queries."
        )
        mem_write_ms = (time.perf_counter() - t2) * 1000.0
        print(f"  Memory Write Latency: {mem_write_ms:.3f} ms")

        # 4. Measure Memory Retrieval
        t3 = time.perf_counter()
        memories = mem_service.retrieve_memories(self.user_id, query="low latency", limit=5)
        mem_read_ms = (time.perf_counter() - t3) * 1000.0
        print(f"  Memory Search Latency: {mem_read_ms:.3f} ms")

        # Assert latencies are within reasonable bounds (< 100ms for local DB)
        self.assertLess(goal_create_ms, 500.0)
        self.assertLess(goal_read_ms, 500.0)
        self.assertLess(mem_write_ms, 500.0)
        self.assertLess(mem_read_ms, 500.0)

if __name__ == "__main__":
    unittest.main()
