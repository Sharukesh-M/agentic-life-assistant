"""
Notification Repository for Proactive Alert History.
Enforces user isolation scoping.
"""

from typing import List, Optional, Any
from datetime import datetime
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.notification import NotificationModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_notification(
        self,
        notification_id: str,
        user_id: str,
        message: str,
        goal_id: Optional[str] = None,
        priority: str = "MEDIUM",
        status: str = "SENT"
    ) -> NotificationModel:
        notif = NotificationModel(
            notification_id=notification_id,
            user_id=user_id,
            goal_id=goal_id,
            message=message,
            priority=priority,
            sent_at=datetime.utcnow(),
            status=status
        )
        self.session.add(notif)
        self.session.commit()
        self.session.refresh(notif)
        return notif

    def list_user_notifications(self, user_id: str) -> List[NotificationModel]:
        return self.session.query(NotificationModel).filter(
            NotificationModel.user_id == user_id
        ).order_by(NotificationModel.sent_at.desc()).all()
