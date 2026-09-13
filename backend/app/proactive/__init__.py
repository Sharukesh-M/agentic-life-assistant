"""
JARVIX Proactive Intelligence System Package.
Includes Observation Collectors, Goal-Event Correlation, Proactive Decision Engine, Quiet Hours Hard Gates, Deduplication, Notification Persistence, and Local Scheduler.
"""

from app.proactive.models import (
    Observation,
    NotificationPreference,
    ProactiveCandidate,
    ProactiveCycleResult
)
from app.proactive.collector import (
    BaseObservationCollector,
    CollectorRegistry,
    MockCalendarObservationCollector,
    MockGitHubObservationCollector,
    MockRSSObservationCollector
)
from app.proactive.correlation import GoalEventCorrelator
from app.proactive.decision import ProactiveDecisionEngine
from app.proactive.deduplication import ProactiveDeduplicator
from app.proactive.scheduler import LocalProactiveScheduler
from app.proactive.service import ProactiveService

__all__ = [
    "Observation",
    "NotificationPreference",
    "ProactiveCandidate",
    "ProactiveCycleResult",
    "BaseObservationCollector",
    "CollectorRegistry",
    "MockCalendarObservationCollector",
    "MockGitHubObservationCollector",
    "MockRSSObservationCollector",
    "GoalEventCorrelator",
    "ProactiveDecisionEngine",
    "ProactiveDeduplicator",
    "LocalProactiveScheduler",
    "ProactiveService"
]
