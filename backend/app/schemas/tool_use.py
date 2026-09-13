"""
Validation Schemas for Tool Execution Discipline & Auditing.
"""

try:
    from pydantic import BaseModel
    from typing import Dict, Any, Optional, Literal

    class ToolCallRequest(BaseModel):
        tool_name: str
        arguments: Dict[str, Any]
        necessity_rationale: str
        authorization_token: Optional[str] = None

    class ToolExecutionResult(BaseModel):
        tool_name: str
        status: Literal["success", "failure", "unauthorized"]
        result_data: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = None
        execution_time_seconds: float = 0.0

except ImportError:
    from dataclasses import dataclass, field
    from typing import Dict, Any, Optional

    @dataclass
    class ToolCallRequest:
        tool_name: str
        arguments: Dict[str, Any]
        necessity_rationale: str
        authorization_token: Optional[str] = None

    @dataclass
    class ToolExecutionResult:
        tool_name: str
        status: str
        result_data: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = None
        execution_time_seconds: float = 0.0
