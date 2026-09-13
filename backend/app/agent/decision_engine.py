"""
JARVIX Decision Engine.
Evaluates Reversibility Test, Confirmation Requirements, and Proactive Gating.
"""

from typing import Dict, Any, Tuple

class DecisionEngine:
    """
    Evaluates action impact and confirmation thresholds.
    """

    @staticmethod
    def is_action_reversible(action_type: str, details: Dict[str, Any]) -> bool:
        """
        Runs the Reversibility Test:
        - Low-impact / easily reversible (e.g. draft text, internal task object) -> True (Proceed)
        - High-impact / hard to reverse (e.g. Google Calendar event, API mutation, remote compute execution) -> False (Require Confirmation)
        """
        high_impact_actions = {
            "calendar_create_event",
            "calendar_delete_event",
            "start_compute_job",
            "send_device_notification",
            "external_api_write"
        }
        if action_type in high_impact_actions or details.get("external_visible", False):
            return False
        return True

    @staticmethod
    def evaluate_proactive_gate(
        relevance_score: float,
        goal_priority: str,
        quiet_hours: bool,
        threshold: float = 0.70
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a candidate proactive notification should be surfaced.
        """
        if quiet_hours:
            return False, "Suppressed due to quiet hours"

        priority_boost = 0.15 if goal_priority == "HIGH" else (0.05 if goal_priority == "MEDIUM" else 0.0)
        final_score = relevance_score + priority_boost

        if final_score >= threshold:
            return True, f"Passed threshold ({final_score:.2f} >= {threshold})"
        return False, f"Below notification threshold ({final_score:.2f} < {threshold})"
