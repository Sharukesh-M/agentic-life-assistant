"""
Proactive Decision Engine.
Evaluates candidate observations against notification policies, quiet hours, frequency thresholds, and safety confirmation gates.
"""

from typing import List, Tuple, Optional
from app.proactive.models import Observation, NotificationPreference, ProactiveCandidate
from app.schemas.goals import GoalEventCorrelationOutput, EventMatchItem
from app.agent.decision_engine import DecisionEngine

class ProactiveDecisionEngine:
    """
    Evaluates candidate observations to decide whether to Notify, Recommend, Ask User, or Ignore.
    Enforces Quiet Hours hard gates and High-Impact confirmation boundaries.
    """

    def __init__(self, base_decision_engine: Optional[DecisionEngine] = None):
        self.decision_engine = base_decision_engine or DecisionEngine()

    def evaluate_candidate(
        self,
        observation: Observation,
        correlation: GoalEventCorrelationOutput,
        preference: NotificationPreference,
        current_hour: int
    ) -> ProactiveCandidate:
        """
        Evaluates an observation against goal correlation and user notification preference.
        """
        candidate = ProactiveCandidate(
            observation=observation,
            goal_matches=correlation.matches,
            highest_relevance_score=0.0,
            highest_priority="LOW",
            decision="ignore",
            reason="No relevant active goals matched."
        )

        if correlation.no_relevant_goals or not correlation.matches:
            return candidate

        # Find top matching goal
        top_match = correlation.matches[0]
        candidate.highest_relevance_score = top_match.relevance_score
        candidate.highest_priority = top_match.goal_priority

        # 1. Frequency Preference Check
        if not preference.notification_enabled or preference.frequency == "NONE":
            candidate.decision = "ignore"
            candidate.is_suppressed = True
            candidate.suppression_reason = "Notifications disabled in user preference."
            return candidate

        threshold_map = {
            "LOW": 0.80,
            "NORMAL": 0.70,
            "HIGH": 0.55
        }
        threshold = threshold_map.get(preference.frequency, 0.70)

        # 2. Quiet Hours Hard Gate Check
        in_quiet_hours = preference.is_in_quiet_hours(current_hour)
        if in_quiet_hours and not preference.emergency_override:
            candidate.decision = "ignore"
            candidate.is_suppressed = True
            candidate.suppression_reason = f"Suppressed due to quiet hours ({preference.quiet_hours_start}:00 to {preference.quiet_hours_end}:00)."
            return candidate

        # 3. Evaluate Proactive Decision Gate via DecisionEngine
        passed, gate_reason = self.decision_engine.evaluate_proactive_gate(
            relevance_score=top_match.relevance_score,
            goal_priority=top_match.goal_priority,
            quiet_hours=in_quiet_hours,
            threshold=threshold
        )

        if not passed:
            candidate.decision = "ignore"
            candidate.reason = gate_reason
            candidate.is_suppressed = True
            candidate.suppression_reason = gate_reason
            return candidate

        # 4. State-Changing Action & High-Impact Confirmation Check
        action = top_match.suggested_action or "recommend"
        state_changing_actions = {"create_task", "reschedule_task", "create_calendar_event", "delete_data", "send_device_notification"}
        
        if action in state_changing_actions or observation.metadata.get("external_visible", False):
            candidate.requires_confirmation = True
            candidate.decision = "ask_user"  # Surface as recommendation requiring user confirmation
            candidate.reason = f"State-changing action '{action}' requires user confirmation before execution."
        elif top_match.relevance_score >= 0.80:
            candidate.decision = "notify"
            candidate.reason = f"High relevance score ({top_match.relevance_score}) for priority goal."
        else:
            candidate.decision = "recommend"
            candidate.reason = f"Relevant item ({top_match.relevance_score}) matched goal."

        return candidate
