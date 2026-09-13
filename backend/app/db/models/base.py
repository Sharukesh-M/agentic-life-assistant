"""
SQLAlchemy Base Model with Declarative Base and Timestamp Mixins.
Supports dataclass / attribute fallback when SQLAlchemy is not installed.
"""

from datetime import datetime
from typing import Any

try:
    from sqlalchemy.orm import declarative_base, declared_attr
    from sqlalchemy import Column, DateTime
    Base = declarative_base()
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    class Base:
        pass

class ColumnStub:
    """Stub column descriptor for in-memory filtering when SQLAlchemy is not installed."""
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return ("eq", self.name, other)

    def __ne__(self, other):
        return ("ne", self.name, other)

    def desc(self):
        return ("desc", self.name)

    def asc(self):
        return ("asc", self.name)

class TimestampMixin:
    """Mixin adding created_at and updated_at timestamps."""
    if HAS_SQLALCHEMY:
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

