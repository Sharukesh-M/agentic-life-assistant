"""
Validation Schemas for JARVIX Orchestrator Routing Outputs.
"""

try:
    from pydantic import BaseModel, Field
    from typing import List, Literal, Optional

    class OrchestratorRouting(BaseModel):
        intent: str
        required_capabilities: List[str] = Field(default_factory=list)
        required_tools: List[str] = Field(default_factory=list)
        authorization_checked: bool = True
        authorization_status: Literal["authorized", "not_authorized", "not_applicable"] = "authorized"
        requires_confirmation: bool = False
        confirmation_prompt: Optional[str] = None

except ImportError:
    from dataclasses import dataclass, field
    from typing import List, Optional

    @dataclass
    class OrchestratorRouting:
        intent: str
        required_capabilities: List[str] = field(default_factory=list)
        required_tools: List[str] = field(default_factory=list)
        authorization_checked: bool = True
        authorization_status: str = "authorized"
        requires_confirmation: bool = False
        confirmation_prompt: Optional[str] = None
