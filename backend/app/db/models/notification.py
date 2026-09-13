"""
Notification Model Entity for Tracking Proactive Alert History.
"""

from datetime import datetime
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, DateTime, ForeignKey, Text
    class NotificationModel(Base):
        __tablename__ = "notifications"

        notification_id = Column(String(64), primary_key=True, index=True)
        user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
        goal_id = Column(String(64), ForeignKey("goals.goal_id"), nullable=True, index=True)
        message = Column(Text, nullable=False)
        priority = Column(String(32), nullable=False, default="MEDIUM") # HIGH | MEDIUM | LOW
        sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        status = Column(String(32), nullable=False, default="SENT")     # SENT | SUPPRESSED | READ
else:
    from app.db.models.base import ColumnStub
    class NotificationModel:
        notification_id = ColumnStub("notification_id")
        user_id = ColumnStub("user_id")
        goal_id = ColumnStub("goal_id")
        message = ColumnStub("message")
        priority = ColumnStub("priority")
        sent_at = ColumnStub("sent_at")
        status = ColumnStub("status")

        def __init__(
            self,
            notification_id: str,
            user_id: str,
            message: str,
            goal_id: str = None,
            priority: str = "MEDIUM",
            sent_at: datetime = None,
            status: str = "SENT"
        ):
            self.notification_id = notification_id
            self.user_id = user_id
            self.goal_id = goal_id
            self.message = message
            self.priority = priority
            self.sent_at = sent_at or datetime.utcnow()
            self.status = status


