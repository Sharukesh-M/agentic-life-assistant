"""
Goal Model Entity.
"""

from datetime import datetime
from typing import Optional
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
    class GoalModel(Base):
        __tablename__ = "goals"

        goal_id = Column(String(64), primary_key=True, index=True)
        user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
        title = Column(String(256), nullable=False)
        category = Column(String(128), nullable=False, default="General")
        description = Column(Text, nullable=True)
        priority = Column(String(32), nullable=False, default="MEDIUM")
        deadline = Column(DateTime, nullable=True)
        status = Column(String(32), nullable=False, default="ACTIVE")
        available_time_per_day = Column(Integer, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class GoalModel:
        goal_id = ColumnStub("goal_id")
        user_id = ColumnStub("user_id")
        title = ColumnStub("title")
        category = ColumnStub("category")
        description = ColumnStub("description")
        priority = ColumnStub("priority")
        deadline = ColumnStub("deadline")
        status = ColumnStub("status")
        available_time_per_day = ColumnStub("available_time_per_day")
        created_at = ColumnStub("created_at")
        updated_at = ColumnStub("updated_at")

        def __init__(
            self,
            goal_id: str,
            user_id: str,
            title: str,
            category: str = "General",
            description: Optional[str] = None,
            priority: str = "MEDIUM",
            deadline: Optional[datetime] = None,
            status: str = "ACTIVE",
            available_time_per_day: Optional[int] = None
        ):
            self.goal_id = goal_id
            self.user_id = user_id
            self.title = title
            self.category = category
            self.description = description
            self.priority = priority
            self.deadline = deadline
            self.status = status
            self.available_time_per_day = available_time_per_day
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

