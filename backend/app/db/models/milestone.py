"""
Milestone Model Entity.
"""

from datetime import datetime
from typing import Optional
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
    class MilestoneModel(Base):
        __tablename__ = "milestones"

        milestone_id = Column(String(64), primary_key=True, index=True)
        goal_id = Column(String(64), ForeignKey("goals.goal_id"), nullable=False, index=True)
        title = Column(String(256), nullable=False)
        description = Column(Text, nullable=True)
        order_index = Column(Integer, nullable=False, default=0)
        status = Column(String(32), nullable=False, default="ACTIVE")
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class MilestoneModel:
        milestone_id = ColumnStub("milestone_id")
        goal_id = ColumnStub("goal_id")
        title = ColumnStub("title")
        description = ColumnStub("description")
        order_index = ColumnStub("order_index")
        status = ColumnStub("status")
        created_at = ColumnStub("created_at")
        updated_at = ColumnStub("updated_at")

        def __init__(
            self,
            milestone_id: str,
            goal_id: str,
            title: str,
            description: Optional[str] = None,
            order_index: int = 0,
            status: str = "ACTIVE"
        ):
            self.milestone_id = milestone_id
            self.goal_id = goal_id
            self.title = title
            self.description = description
            self.order_index = order_index
            self.status = status
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

