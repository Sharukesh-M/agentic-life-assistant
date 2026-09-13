"""
Validation Schemas for Goal Record & Goal-Event Correlation.
"""

try:
    from pydantic import BaseModel, Field
    from typing import List, Literal, Optional

    class GoalRecord(BaseModel):
        goal_id: str
        title: str
        category: str
        description: str
        priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
        deadline: Optional[str] = None
        status: Literal["ACTIVE", "PAUSED", "COMPLETED", "ABANDONED"] = "ACTIVE"
        available_time_per_day: Optional[int] = None

    class EventMatchItem(BaseModel):
        goal_id: str
        relevance_score: float = Field(ge=0.0, le=1.0)
        goal_priority: Literal["HIGH", "MEDIUM", "LOW"]
        reason: str
        suggested_action: str

    class GoalEventCorrelationOutput(BaseModel):
        matches: List[EventMatchItem] = Field(default_factory=list)
        no_relevant_goals: bool = False

except ImportError:
    from dataclasses import dataclass, field
    from typing import List, Optional

    @dataclass
    class GoalRecord:
        goal_id: str
        title: str
        category: str
        description: str
        priority: str = "MEDIUM"
        deadline: Optional[str] = None
        status: str = "ACTIVE"
        available_time_per_day: Optional[int] = None

    @dataclass
    class EventMatchItem:
        goal_id: str
        relevance_score: float
        goal_priority: str
        reason: str
        suggested_action: str

    @dataclass
    class GoalEventCorrelationOutput:
        matches: List[EventMatchItem] = field(default_factory=list)
        no_relevant_goals: bool = False
