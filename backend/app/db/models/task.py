"""
Task Model Entity.
"""

from datetime import datetime
from typing import Optional
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
    class TaskModel(Base):
        __tablename__ = "tasks"

        task_id = Column(String(64), primary_key=True, index=True)
        goal_id = Column(String(64), ForeignKey("goals.goal_id"), nullable=False, index=True)
        milestone_id = Column(String(64), ForeignKey("milestones.milestone_id"), nullable=True, index=True)
        user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
        title = Column(String(256), nullable=False)
        description = Column(Text, nullable=True)
        priority = Column(String(32), nullable=False, default="MEDIUM")
        deadline = Column(DateTime, nullable=True)
        estimated_minutes = Column(Integer, nullable=False, default=30)
        status = Column(String(32), nullable=False, default="CREATED")
        depends_on = Column(Text, nullable=True)
        completion_source = Column(String(128), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class TaskModel:
        task_id = ColumnStub("task_id")
        goal_id = ColumnStub("goal_id")
        milestone_id = ColumnStub("milestone_id")
        user_id = ColumnStub("user_id")
        title = ColumnStub("title")
        description = ColumnStub("description")
        priority = ColumnStub("priority")
        deadline = ColumnStub("deadline")
        estimated_minutes = ColumnStub("estimated_minutes")
        status = ColumnStub("status")
        depends_on = ColumnStub("depends_on")
        completion_source = ColumnStub("completion_source")
        created_at = ColumnStub("created_at")
        updated_at = ColumnStub("updated_at")

        def __init__(
            self,
            task_id: str,
            goal_id: str,
            user_id: str,
            title: str,
            milestone_id: Optional[str] = None,
            description: Optional[str] = None,
            priority: str = "MEDIUM",
            deadline: Optional[datetime] = None,
            estimated_minutes: int = 30,
            status: str = "CREATED",
            depends_on: Optional[str] = None,
            completion_source: Optional[str] = None
        ):
            self.task_id = task_id
            self.goal_id = goal_id
            self.milestone_id = milestone_id
            self.user_id = user_id
            self.title = title
            self.description = description
            self.priority = priority
            self.deadline = deadline
            self.estimated_minutes = estimated_minutes
            self.status = status
            self.depends_on = depends_on
            self.completion_source = completion_source
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

