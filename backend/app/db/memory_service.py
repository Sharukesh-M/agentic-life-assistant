"""
High-Level Memory Service.
Centralizes memory storage, safety inspection, deduplication, contradiction updates, and user-isolated retrieval.
"""

import uuid
from typing import List, Optional, Any
from app.db.models.base import HAS_SQLALCHEMY
from app.db.repositories.memory_repository import MemoryRepository, SensitiveDataViolation
from app.db.models.memory import MemoryRecordModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class MemoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = MemoryRepository(session)

    def store_memory(
        self,
        user_id: str,
        classification: str,
        content: str,
        source: str = "user_interaction",
        importance: float = 1.0
    ) -> MemoryRecordModel:
        """
        Stores durable memory with safety policy, deduplication, and contradiction resolution.
        """
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        return self.repo.store_memory(
            memory_id=memory_id,
            user_id=user_id,
            classification=classification,
            content=content,
            source=source,
            importance=importance
        )

    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[MemoryRecordModel]:
        """
        Retrieves relevant active long-term memories for given user query.
        """
        return self.repo.search_memories(user_id=user_id, query=query, limit=limit)

    def list_active_memories(self, user_id: str) -> List[MemoryRecordModel]:
        """
        Lists all active memories for given user.
        """
        return self.repo.list_active_memories(user_id=user_id)

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """
        Soft deletes (deactivates) a memory record for given user.
        """
        record = self.session.query(MemoryRecordModel).filter(
            MemoryRecordModel.memory_id == memory_id,
            MemoryRecordModel.user_id == user_id
        ).first()
        if record:
            record.is_active = False
            self.session.commit()
            return True
        return False
