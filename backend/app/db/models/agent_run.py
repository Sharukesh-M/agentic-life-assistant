"""
Agent Run Log Model Entity for Observability.
"""

from datetime import datetime
from typing import Optional
from app.db.models.base import Base, HAS_SQLALCHEMY

if HAS_SQLALCHEMY:
    from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
    class AgentRunModel(Base):
        __tablename__ = "agent_runs"

        run_id = Column(String(64), primary_key=True, index=True)
        user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
        intent = Column(String(128), nullable=False)
        required_capabilities = Column(Text, nullable=True)
        required_tools = Column(Text, nullable=True)
        provider = Column(String(64), nullable=False)
        model = Column(String(128), nullable=False)
        confirmation_required = Column(Boolean, nullable=False, default=False)
        execution_status = Column(String(32), nullable=False, default="completed")
        validation_status = Column(String(32), nullable=False, default="valid")
        error_type = Column(String(128), nullable=True)
        latency_ms = Column(Float, nullable=False, default=0.0)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
else:
    from app.db.models.base import ColumnStub
    class AgentRunModel:
        run_id = ColumnStub("run_id")
        user_id = ColumnStub("user_id")
        intent = ColumnStub("intent")
        required_capabilities = ColumnStub("required_capabilities")
        required_tools = ColumnStub("required_tools")
        provider = ColumnStub("provider")
        model = ColumnStub("model")
        confirmation_required = ColumnStub("confirmation_required")
        execution_status = ColumnStub("execution_status")
        validation_status = ColumnStub("validation_status")
        error_type = ColumnStub("error_type")
        latency_ms = ColumnStub("latency_ms")
        created_at = ColumnStub("created_at")

        def __init__(
            self,
            run_id: str,
            user_id: str,
            intent: str,
            provider: str,
            model: str,
            required_capabilities: Optional[str] = None,
            required_tools: Optional[str] = None,
            confirmation_required: bool = False,
            execution_status: str = "completed",
            validation_status: str = "valid",
            error_type: Optional[str] = None,
            latency_ms: float = 0.0
        ):
            self.run_id = run_id
            self.user_id = user_id
            self.intent = intent
            self.required_capabilities = required_capabilities
            self.required_tools = required_tools
            self.provider = provider
            self.model = model
            self.confirmation_required = confirmation_required
            self.execution_status = execution_status
            self.validation_status = validation_status
            self.error_type = error_type
            self.latency_ms = latency_ms
            self.created_at = datetime.utcnow()

