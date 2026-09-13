"""
Proactive Intelligence System Domain Models.
Observation abstractions, Notification Preferences, Candidate items, and Cycle Results.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field
from app.schemas.goals import EventMatchItem

@dataclass
class Observation:
    observation_id: str
    source: str           # e.g., "mock_calendar", "mock_github", "mock_rss"
    source_type: str      # "calendar", "github", "rss", "system"
    title: str
    summary: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationPreference:
    user_id: str
    notification_enabled: bool = True
    frequency: str = "NORMAL"  # "NONE" | "LOW" | "NORMAL" | "HIGH"
    quiet_hours_enabled: bool = True
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 7     # 7 AM
    emergency_override: bool = False

    def is_in_quiet_hours(self, current_hour: int) -> bool:
        """Checks if given hour (0-23) falls within quiet hours."""
        if not self.quiet_hours_enabled:
            return False
        if self.quiet_hours_start > self.quiet_hours_end:
            # Overnight interval (e.g. 22:00 to 07:00)
            return current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end
        else:
            # Daytime interval (e.g. 01:00 to 06:00)
            return self.quiet_hours_start <= current_hour < self.quiet_hours_end

@dataclass
class ProactiveCandidate:
    observation: Observation
    goal_matches: List[EventMatchItem] = field(default_factory=list)
    highest_relevance_score: float = 0.0
    highest_priority: str = "LOW"
    decision: str = "ignore"  # "notify" | "recommend" | "create_task" | "ask_user" | "ignore"
    reason: str = ""
    requires_confirmation: bool = False
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None

@dataclass
class ProactiveCycleResult:
    cycle_time: datetime
    user_id: str
    observations_collected: int
    candidates_evaluated: int
    notifications_sent: int
    notifications_suppressed: int
    surfaced_messages: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
