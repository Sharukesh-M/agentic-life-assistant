"""
Persistent Memory Record Model.
"""

from datetime import datetime
from typing import Optional
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean
    class MemoryRecordModel(Base):
        __tablename__ = "memory_records"

        memory_id = Column(String(64), primary_key=True, index=True)
        user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
        classification = Column(String(64), nullable=False)
        content = Column(Text, nullable=False)
        source = Column(String(128), nullable=False, default="user_interaction")
        importance = Column(Float, nullable=False, default=1.0)
        is_active = Column(Boolean, nullable=False, default=True)
        superseded_by_id = Column(String(64), nullable=True)
        metadata_json = Column(Text, nullable=True)
        embedding_json = Column(Text, nullable=True)
        last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class MemoryRecordModel:
        memory_id = ColumnStub("memory_id")
        user_id = ColumnStub("user_id")
        classification = ColumnStub("classification")
        content = ColumnStub("content")
        source = ColumnStub("source")
        importance = ColumnStub("importance")
        is_active = ColumnStub("is_active")
        superseded_by_id = ColumnStub("superseded_by_id")
        metadata_json = ColumnStub("metadata_json")
        embedding_json = ColumnStub("embedding_json")
        last_accessed_at = ColumnStub("last_accessed_at")
        created_at = ColumnStub("created_at")
        updated_at = ColumnStub("updated_at")

        def __init__(
            self,
            memory_id: str,
            user_id: str,
            classification: str,
            content: str,
            source: str = "user_interaction",
            importance: float = 1.0,
            is_active: bool = True,
            superseded_by_id: Optional[str] = None,
            metadata_json: Optional[str] = None,
            embedding_json: Optional[str] = None,
            last_accessed_at: Optional[datetime] = None
        ):
            self.memory_id = memory_id
            self.user_id = user_id
            self.classification = classification
            self.content = content
            self.source = source
            self.importance = importance
            self.is_active = is_active
            self.superseded_by_id = superseded_by_id
            self.metadata_json = metadata_json
            self.embedding_json = embedding_json
            self.last_accessed_at = last_accessed_at or datetime.utcnow()
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

