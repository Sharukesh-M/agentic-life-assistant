"""
Database Configuration Module.
Supports PostgreSQL (with optional pgvector) and SQLite local development/test fallback.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DBConfig:
    database_url: str
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    @classmethod
    def from_env(cls) -> 'DBConfig':
        # Default to local SQLite database if DATABASE_URL is not set
        url = os.getenv("DATABASE_URL", "sqlite:///./jarvix.db")
        # Support postgresql:// -> postgresql+psycopg2:// if needed
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        echo = os.getenv("DB_ECHO", "false").lower() == "true"
        return cls(
            database_url=url,
            echo_sql=echo,
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10"))
        )

    def get_active_backend(self) -> str:
        """Explicitly identifies whether active backend is POSTGRESQL, SQLITE, or IN_MEMORY."""
        from app.db.models.base import HAS_SQLALCHEMY
        if not HAS_SQLALCHEMY:
            return "IN_MEMORY"
        url = self.database_url.lower()
        if url.startswith("postgresql") or url.startswith("postgres"):
            return "POSTGRESQL"
        elif url.startswith("sqlite"):
            return "SQLITE"
        return "UNKNOWN"

