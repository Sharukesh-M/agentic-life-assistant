"""
Validation Schemas for JARVIX Planning Agent Outputs.
Supports Pydantic when installed, with Dataclass fallback when pydantic is not installed.
"""

try:
    from pydantic import BaseModel, Field
    from typing import List, Literal, Optional

    class TaskItem(BaseModel):
        title: str
        description: str
        priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
        estimated_minutes: int = Field(ge=0, default=30)
        depends_on: List[str] = Field(default_factory=list)

    class MilestoneItem(BaseModel):
        title: str
        description: str
        tasks: List[TaskItem] = Field(default_factory=list)

    class PlanOutput(BaseModel):
        status: Literal["plan"] = "plan"
        goal: str
        assumptions: List[str] = Field(default_factory=list)
        milestones: List[MilestoneItem] = Field(default_factory=list)

    class ClarificationOutput(BaseModel):
        status: Literal["clarification_needed"] = "clarification_needed"
        questions: List[str] = Field(default_factory=list)

except ImportError:
    from dataclasses import dataclass, field
    from typing import List, Optional

    @dataclass
    class TaskItem:
        title: str
        description: str
        priority: str = "MEDIUM"
        estimated_minutes: int = 30
        depends_on: List[str] = field(default_factory=list)

    @dataclass
    class MilestoneItem:
        title: str
        description: str
        tasks: List[TaskItem] = field(default_factory=list)

    @dataclass
    class PlanOutput:
        goal: str
        status: str = "plan"
        assumptions: List[str] = field(default_factory=list)
        milestones: List[MilestoneItem] = field(default_factory=list)

    @dataclass
    class ClarificationOutput:
        questions: List[str] = field(default_factory=list)
        status: str = "clarification_needed"
