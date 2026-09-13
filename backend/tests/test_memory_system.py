"""
Memory System Unit Tests.
Tests classification policy, sensitive data safety gate, deduplication, contradiction handling, and user isolation.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory
from app.db.repositories.user_repository import UserRepository
from app.db.memory_service import MemoryService
from app.db.repositories.memory_repository import SensitiveDataViolation

class TestMemorySystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DBConfig(database_url="sqlite:///:memory:")
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.session = self.SessionFactory()
        user_repo = UserRepository(self.session)
        user_repo.get_or_create("mem_user_1")
        user_repo.get_or_create("mem_user_2")
        self.service = MemoryService(self.session)

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_store_and_retrieve_valid_memory(self):
        mem = self.service.store_memory(
            user_id="mem_user_1",
            classification="LONG_TERM_PREFERENCE",
            content="Prefers worked examples in Python for learning AI.",
            importance=1.0
        )
        self.assertEqual(mem.classification, "LONG_TERM_PREFERENCE")

        retrieved = self.service.retrieve_memories("mem_user_1", query="Python learning", limit=5)
        self.assertEqual(len(retrieved), 1)
        self.assertIn("worked examples", retrieved[0].content)

    def test_classification_policy_gate(self):
        """Temporary context must NOT be stored as durable long-term memory."""
        with self.assertRaises(ValueError):
            self.service.store_memory(
                user_id="mem_user_1",
                classification="TEMPORARY_CONTEXT",
                content="What time is it right now?"
            )

    def test_sensitive_data_safety_gate(self):
        """Sensitive credentials (API keys, cards, passwords) must be BLOCKED from memory storage."""
        sensitive_samples = [
            "My secret API key is api_key=sk-1234567890abcdef",
            "My credit card number is 4111-2222-3333-4444",
            "My login password is password=SuperSecretPass123"
        ]
        for sample in sensitive_samples:
            with self.assertRaises(SensitiveDataViolation):
                self.service.store_memory(
                    user_id="mem_user_1",
                    classification="LONG_TERM_PREFERENCE",
                    content=sample
                )

    def test_memory_deduplication(self):
        """Identical memory text must NOT create duplicate DB rows."""
        content = "Prefers dark mode interface themes."
        m1 = self.service.store_memory("mem_user_1", "LONG_TERM_PREFERENCE", content)
        m2 = self.service.store_memory("mem_user_1", "LONG_TERM_PREFERENCE", content)
        self.assertEqual(m1.memory_id, m2.memory_id)

    def test_contradiction_management(self):
        """New preference must supersede old contradictory preference."""
        m_old = self.service.store_memory("mem_user_1", "LONG_TERM_PREFERENCE", "Prefers evening study sessions.")
        self.assertTrue(m_old.is_active)

        m_new = self.service.store_memory("mem_user_1", "LONG_TERM_PREFERENCE", "Prefers morning study sessions.")
        self.assertTrue(m_new.is_active)

        self.session.refresh(m_old)
        self.assertFalse(m_old.is_active)
        self.assertEqual(m_old.superseded_by_id, m_new.memory_id)

    def test_memory_user_security_isolation(self):
        """User A memories must NEVER be accessible to User B."""
        self.service.store_memory("mem_user_1", "LONG_TERM_PREFERENCE", "User 1 secret preference")
        
        user_2_memories = self.service.retrieve_memories("mem_user_2", query="secret", limit=5)
        self.assertEqual(len(user_2_memories), 0)

if __name__ == "__main__":
    unittest.main()
