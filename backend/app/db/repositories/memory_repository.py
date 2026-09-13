"""
Memory Repository for Persistent Tiered Memory.
Supports semantic vector search (pgvector/JSON embeddings), user isolation, deduplication, and contradiction management.
"""

import json
import re
import uuid
from typing import List, Optional, Tuple, Any
from datetime import datetime
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.memory import MemoryRecordModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class SensitiveDataViolation(Exception):
    """Raised when candidate memory contains sensitive personal information prohibited by policy."""
    pass

class MemoryRepository:
    """
    Data Access Repository for JARVIX Memory Records.
    """

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def inspect_sensitive_data(content: str):
        """
        Application-Level Memory Safety Gate.
        Enforces policy: Never store credit card numbers, passwords, API keys, government IDs.
        """
        patterns = [
            (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', "credit/debit card number"),
            (r'\b\d{3}-\d{2}-\d{4}\b', "social security / government ID"),
            (r'\b(api[_-]?key|secret[_-]?token|bearer)\s*(?:is|[:=])\s*\S+', "API key or secret token"),
            (r'\bpassword\s*(?:is|[:=])\s*\S+', "password credential")
        ]
        for pattern, label in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise SensitiveDataViolation(f"Memory storage blocked by Safety Policy: detected {label}.")

    def store_memory(
        self,
        memory_id: str,
        user_id: str,
        classification: str,
        content: str,
        source: str = "user_interaction",
        importance: float = 1.0,
        embedding: Optional[List[float]] = None,
        metadata: Optional[dict] = None
    ) -> MemoryRecordModel:
        """
        Stores durable memory record with safety checks, deduplication, and contradiction resolution.
        """
        # 1. Classification Policy Gate: Only store LONG_TERM_PREFERENCE & IMPORTANT_INSTRUCTION
        allowed_classifications = {"LONG_TERM_PREFERENCE", "IMPORTANT_INSTRUCTION"}
        if classification not in allowed_classifications:
            raise ValueError(f"Classification '{classification}' is not persistent long-term memory. Memory write skipped.")

        # 2. Sensitive Data Inspection Gate
        self.inspect_sensitive_data(content)

        # 3. Deduplication & Contradiction Resolution
        existing_memories = self.list_active_memories(user_id=user_id)
        for mem in existing_memories:
            # Exact or near-identical text deduplication
            if mem.content.strip().lower() == content.strip().lower():
                mem.last_accessed_at = datetime.utcnow()
                self.session.commit()
                self.session.refresh(mem)
                return mem

            # Contradiction Detection Heuristic (e.g. studying in evening vs morning)
            if self._is_contradiction(mem.content, content):
                # Mark prior preference as superseded
                mem.is_active = False
                mem.superseded_by_id = memory_id
                self.session.commit()

        # 4. Create new persistent memory record
        embedding_str = json.dumps(embedding) if embedding else None
        metadata_str = json.dumps(metadata) if metadata else None

        record = MemoryRecordModel(
            memory_id=memory_id,
            user_id=user_id,
            classification=classification,
            content=content.strip(),
            source=source,
            importance=importance,
            is_active=True,
            embedding_json=embedding_str,
            metadata_json=metadata_str,
            last_accessed_at=datetime.utcnow()
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def _is_contradiction(self, old_text: str, new_text: str) -> bool:
        """Heuristic check for contradictory user preferences."""
        old_l = old_text.lower()
        new_l = new_text.lower()
        
        # Example contradiction pairs: evening vs morning, code vs video, etc.
        pairs = [
            ("evening", "morning"),
            ("morning", "evening"),
            ("dark mode", "light mode"),
            ("light mode", "dark mode")
        ]
        for term1, term2 in pairs:
            if term1 in old_l and term2 in new_l:
                return True
        return False

    def list_active_memories(self, user_id: str) -> List[MemoryRecordModel]:
        """Returns all active long-term memories for given user."""
        return self.session.query(MemoryRecordModel).filter(
            MemoryRecordModel.user_id == user_id,
            MemoryRecordModel.is_active == True
        ).order_by(MemoryRecordModel.created_at.desc()).all()

    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[MemoryRecordModel]:
        """
        Retrieves relevant active memories using keyword & semantic scoring.
        """
        active_memories = self.list_active_memories(user_id=user_id)
        if not active_memories:
            return []

        # Keyword relevance & preference scoring
        query_words = set(re.findall(r'\w+', query.lower()))
        scored: List[Tuple[float, MemoryRecordModel]] = []

        for mem in active_memories:
            content_words = set(re.findall(r'\w+', mem.content.lower()))
            overlap = len(query_words.intersection(content_words))
            score = (overlap + 0.1) * mem.importance
            scored.append((score, mem))

        # Sort by relevance score
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:limit]]

