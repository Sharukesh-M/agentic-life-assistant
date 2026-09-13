"""
User Repository for Managing User Persistence.
"""

from typing import Optional, Any
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.user import UserModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, user_id: str) -> UserModel:
        user = self.session.query(UserModel).filter(UserModel.user_id == user_id).first()
        if not user:
            user = UserModel(user_id=user_id)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        return user
