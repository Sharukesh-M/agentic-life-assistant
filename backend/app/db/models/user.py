"""
User Model Entity.
"""

from datetime import datetime
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, DateTime
    class UserModel(Base):
        __tablename__ = "users"

        user_id = Column(String(64), primary_key=True, index=True)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class UserModel:
        user_id = ColumnStub("user_id")
        created_at = ColumnStub("created_at")
        updated_at = ColumnStub("updated_at")

        def __init__(self, user_id: str):
            self.user_id = user_id
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

