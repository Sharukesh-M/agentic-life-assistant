"""
Validation Schemas for Proactive Monitor Outputs.
"""

try:
    from pydantic import BaseModel, Field
    from typing import List, Literal, Optional

    class ProactiveNotificationItem(BaseModel):
        goal_id: str
        message: str
        priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
        requires_confirmation: bool = False

    class ProactiveMonitorOutput(BaseModel):
        cycle_time: str
        notifications: List[ProactiveNotificationItem] = Field(default_factory=list)

except ImportError:
    from dataclasses import dataclass, field
    from typing import List, Optional

    @dataclass
    class ProactiveNotificationItem:
        goal_id: str
        message: str
        priority: str = "MEDIUM"
        requires_confirmation: bool = False

    @dataclass
    class ProactiveMonitorOutput:
        cycle_time: str
        notifications: List[ProactiveNotificationItem] = field(default_factory=list)
