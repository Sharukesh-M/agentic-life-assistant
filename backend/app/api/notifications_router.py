"""
JARVIX Notifications REST API Router.
Endpoints for reading, marking, and dismissing proactive notifications.
"""

from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models.base import HAS_SQLALCHEMY
from app.db.repositories.notification_repository import NotificationRepository

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    notification_id: str
    user_id: str
    goal_id: Optional[str] = None
    message: str
    priority: str
    status: str
    sent_at: Optional[str] = None


def _serialize_notification(n) -> dict:
    return NotificationResponse(
        notification_id=n.notification_id,
        user_id=n.user_id,
        goal_id=getattr(n, "goal_id", None),
        message=n.message,
        priority=getattr(n, "priority", "MEDIUM"),
        status=getattr(n, "status", "SENT"),
        sent_at=str(n.sent_at) if getattr(n, "sent_at", None) else None,
    ).model_dump()


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    repo = NotificationRepository(db)
    notifications = repo.list_user_notifications(user_id)
    return [_serialize_notification(n) for n in notifications]


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    repo = NotificationRepository(db)
    notifications = repo.list_user_notifications(user_id)
    target = next((n for n in notifications if n.notification_id == notification_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found.")
    target.status = "READ"
    db.commit()
    return _serialize_notification(target)


@router.patch("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    repo = NotificationRepository(db)
    notifications = repo.list_user_notifications(user_id)
    target = next((n for n in notifications if n.notification_id == notification_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found.")
    target.status = "DISMISSED"
    db.commit()
    return _serialize_notification(target)
