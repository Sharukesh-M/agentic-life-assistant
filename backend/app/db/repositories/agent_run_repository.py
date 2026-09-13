"""
Agent Run Repository for Observability & Execution Logs.
Enforces user isolation scoping.
"""

import json
from typing import List, Optional, Any
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.agent_run import AgentRunModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class AgentRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run_record(
        self,
        run_id: str,
        user_id: str,
        intent: str,
        required_capabilities: list,
        required_tools: list,
        provider: str,
        model: str,
        confirmation_required: bool = False,
        execution_status: str = "completed",
        validation_status: str = "valid",
        error_type: Optional[str] = None,
        latency_ms: float = 0.0
    ) -> AgentRunModel:
        run = AgentRunModel(
            run_id=run_id,
            user_id=user_id,
            intent=intent,
            required_capabilities=json.dumps(required_capabilities),
            required_tools=json.dumps(required_tools),
            provider=provider,
            model=model,
            confirmation_required=confirmation_required,
            execution_status=execution_status,
            validation_status=validation_status,
            error_type=error_type,
            latency_ms=latency_ms
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def list_user_runs(self, user_id: str, limit: int = 20) -> List[AgentRunModel]:
        return self.session.query(AgentRunModel).filter(
            AgentRunModel.user_id == user_id
        ).order_by(AgentRunModel.created_at.desc()).limit(limit).all()
