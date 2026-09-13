"""
Proactive Service Orchestrator.
Coordinates Observation Collectors, Goal-Event Correlation, Proactive Decision Engine, Deduplication, Notification Persistence, and AgentRun Observability.
"""

import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.proactive.models import (
    Observation,
    NotificationPreference,
    ProactiveCandidate,
    ProactiveCycleResult
)
from app.proactive.collector import CollectorRegistry, MockCalendarObservationCollector, MockGitHubObservationCollector, MockRSSObservationCollector
from app.proactive.correlation import GoalEventCorrelator
from app.proactive.decision import ProactiveDecisionEngine
from app.proactive.deduplication import ProactiveDeduplicator
from app.llm.base import BaseLLMProvider
from app.llm.provider import get_llm_provider

class ProactiveService:
    """
    JARVIX Master Proactive Intelligence Orchestrator.
    """

    def __init__(
        self,
        collector_registry: Optional[CollectorRegistry] = None,
        correlator: Optional[GoalEventCorrelator] = None,
        decision_engine: Optional[ProactiveDecisionEngine] = None,
        deduplicator: Optional[ProactiveDeduplicator] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.collector_registry = collector_registry or CollectorRegistry()
        # Initialize default mock collectors if empty
        if not self.collector_registry.list_collectors():
            self.collector_registry.register(MockCalendarObservationCollector())
            self.collector_registry.register(MockGitHubObservationCollector())
            self.collector_registry.register(MockRSSObservationCollector())

        self.correlator = correlator or GoalEventCorrelator(llm_provider=llm_provider)
        self.decision_engine = decision_engine or ProactiveDecisionEngine()
        self.deduplicator = deduplicator or ProactiveDeduplicator()
        self.llm_provider = llm_provider or get_llm_provider()

        # In-memory preference store per user (fallback if DB unconfigured)
        self._user_preferences: Dict[str, NotificationPreference] = {}

    def get_user_preference(self, user_id: str) -> NotificationPreference:
        """Retrieves or creates default notification preferences for user."""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = NotificationPreference(user_id=user_id)
        return self._user_preferences[user_id]

    def set_user_preference(self, preference: NotificationPreference) -> None:
        """Sets custom notification preferences for user."""
        self._user_preferences[preference.user_id] = preference

    def run_cycle(
        self,
        user_id: str,
        current_time: Optional[datetime] = None,
        db_session: Optional[Any] = None
    ) -> ProactiveCycleResult:
        """
        Executes complete proactive check cycle for user_id.
        """
        start_time = time.time()
        now = current_time or datetime.utcnow()
        current_hour = now.hour

        # 1. Load User Preferences
        pref = self.get_user_preference(user_id)

        # 2. Load Active Goals & Tasks from DB (or fallback)
        active_goals = []
        if db_session:
            try:
                from app.db.repositories.goal_repository import GoalRepository
                goal_repo = GoalRepository(db_session)
                active_goals = goal_repo.list_active_goals(user_id)
            except Exception as e:
                print(f"[Proactive Service DB Error] Failed to load goals: {e}")

        # 3. Collect Fresh Observations
        raw_observations = self.collector_registry.collect_all(user_id)

        # 4. Filter already-processed observations (Freshness rule)
        fresh_observations: List[Observation] = []
        for obs in raw_observations:
            if not self.deduplicator.is_observation_processed(user_id, obs.observation_id):
                fresh_observations.append(obs)
                self.deduplicator.mark_observation_processed(user_id, obs.observation_id)

        # 5. Correlate and Evaluate Candidates
        candidates: List[ProactiveCandidate] = []
        surfaced_candidates: List[ProactiveCandidate] = []
        suppressed_count = 0

        for obs in fresh_observations:
            correlation = self.correlator.correlate(obs, active_goals)
            cand = self.decision_engine.evaluate_candidate(obs, correlation, pref, current_hour)
            candidates.append(cand)

            if cand.is_suppressed or cand.decision == "ignore":
                suppressed_count += 1
            else:
                # 6. Deduplication Check against recently sent notifications
                g_id = cand.goal_matches[0].goal_id if cand.goal_matches else "general"
                if self.deduplicator.is_duplicate_notification(user_id, g_id, obs.title):
                    cand.is_suppressed = True
                    cand.suppression_reason = "Duplicate or highly similar notification recently surfaced."
                    suppressed_count += 1
                else:
                    surfaced_candidates.append(cand)

        # 7. Consolidation: Group related candidates into single proactive summary
        surfaced_messages = self._consolidate_candidates(surfaced_candidates, user_id, db_session)

        # Record sent notifications in deduplicator history
        for msg_item in surfaced_messages:
            self.deduplicator.mark_notification_sent(
                user_id=user_id,
                goal_id=msg_item.get("goal_id", "general"),
                message=msg_item.get("message", "")
            )

        latency_ms = (time.time() - start_time) * 1000.0
        cycle_result = ProactiveCycleResult(
            cycle_time=now,
            user_id=user_id,
            observations_collected=len(raw_observations),
            candidates_evaluated=len(candidates),
            notifications_sent=len(surfaced_messages),
            notifications_suppressed=suppressed_count,
            surfaced_messages=surfaced_messages,
            latency_ms=latency_ms
        )

        # 8. AgentRun Observability Logging
        if db_session:
            self._log_proactive_run(cycle_result, db_session)

        return cycle_result

    def _consolidate_candidates(
        self,
        surfaced_candidates: List[ProactiveCandidate],
        user_id: str,
        db_session: Optional[Any]
    ) -> List[Dict[str, Any]]:
        """
        Consolidates candidate items into clean, structured proactive messages.
        Answers: Why am I seeing this? Which goal? What changed? Suggested next step?
        Persists into NotificationRepository if session available.
        """
        if not surfaced_candidates:
            return []

        surfaced_messages: List[Dict[str, Any]] = []

        # If multiple candidates exist for same check, consolidate into single structured item
        for cand in surfaced_candidates:
            obs = cand.observation
            top_match = cand.goal_matches[0] if cand.goal_matches else None
            g_id = top_match.goal_id if top_match else "general"

            msg = (
                f"Proactive Alert for your active goal.\n"
                f"• Event: {obs.title}\n"
                f"• Why it matters: {obs.summary}\n"
                f"• Suggested action: {top_match.suggested_action if top_match else 'Review at your convenience.'}"
            )

            notif_id = f"notif_{uuid.uuid4().hex[:12]}"
            msg_data = {
                "notification_id": notif_id,
                "user_id": user_id,
                "goal_id": g_id,
                "title": obs.title,
                "message": msg,
                "priority": cand.highest_priority,
                "decision": cand.decision,
                "requires_confirmation": cand.requires_confirmation
            }
            surfaced_messages.append(msg_data)

            # Persist to Database NotificationRepository if available
            if db_session:
                try:
                    from app.db.repositories.notification_repository import NotificationRepository
                    notif_repo = NotificationRepository(db_session)
                    notif_repo.create_notification(
                        notification_id=notif_id,
                        user_id=user_id,
                        goal_id=g_id,
                        message=msg,
                        priority=cand.highest_priority
                    )
                except Exception as e:
                    print(f"[Proactive Notification DB Error] {e}")

        return surfaced_messages

    def _log_proactive_run(self, result: ProactiveCycleResult, db_session: Any) -> None:
        """Logs proactive execution run in AgentRunRepository for observability."""
        try:
            from app.db.repositories.agent_run_repository import AgentRunRepository
            run_repo = AgentRunRepository(db_session)
            run_id = f"run_{uuid.uuid4().hex[:12]}"

            run_repo.create_run_record(
                run_id=run_id,
                user_id=result.user_id,
                intent="proactive_monitoring",
                required_capabilities=["proactive_monitor", "goal_correlation"],
                required_tools=["collector_registry"],
                provider="mock_proactive_engine",
                model="jarvix-proactive-v1",
                execution_status="completed",
                validation_status="valid",
                latency_ms=result.latency_ms
            )
        except Exception as e:
            print(f"[Proactive Run Log Error] {e}")
