"""
Proactive Notification & Observation Deduplicator.
Prevents duplicate notifications, repetitive alerts, and spamming the user.
"""

import time
import re
from typing import Set, Dict, Tuple, List, Optional

class ProactiveDeduplicator:
    """
    Manages state for processed observations and recently sent proactive notifications per user.
    """

    def __init__(self, deduplication_window_seconds: float = 86400.0):  # Default 24 hours
        self.deduplication_window_seconds = deduplication_window_seconds
        # Mapping: user_id -> Set of observation_ids
        self._processed_observations: Dict[str, Set[str]] = {}
        # Mapping: user_id -> List of (timestamp, goal_id, message_hash_words)
        self._sent_notifications_history: Dict[str, List[Tuple[float, str, Set[str]]]] = {}

    def is_observation_processed(self, user_id: str, observation_id: str) -> bool:
        """Checks if observation ID has already been processed for user."""
        user_set = self._processed_observations.get(user_id, set())
        return observation_id in user_set

    def mark_observation_processed(self, user_id: str, observation_id: str) -> None:
        """Marks observation ID as processed for user."""
        if user_id not in self._processed_observations:
            self._processed_observations[user_id] = set()
        self._processed_observations[user_id].add(observation_id)

    @staticmethod
    def _extract_words(text: str) -> Set[str]:
        """Extracts lowercase word tokens from message for fuzzy duplicate comparison."""
        return set(re.findall(r'\w+', text.lower()))

    def is_duplicate_notification(
        self,
        user_id: str,
        goal_id: str,
        message: str,
        now_ts: Optional[float] = None
    ) -> bool:
        """
        Checks if a similar notification has already been surfaced for goal within deduplication window.
        Fuzzy overlap >= 70% word match for same goal_id triggers duplicate suppression.
        """
        now = now_ts if now_ts is not None else time.time()
        history = self._sent_notifications_history.get(user_id, [])
        message_words = self._extract_words(message)

        if not message_words:
            return False

        # Filter active history within window
        valid_history = []
        for ts, g_id, words in history:
            if (now - ts) <= self.deduplication_window_seconds:
                valid_history.append((ts, g_id, words))
                if g_id == goal_id:
                    # Calculate word overlap Jaccard similarity
                    intersection = len(message_words.intersection(words))
                    union = len(message_words.union(words))
                    overlap_ratio = intersection / union if union > 0 else 0.0
                    if overlap_ratio >= 0.60:
                        return True

        self._sent_notifications_history[user_id] = valid_history
        return False

    def mark_notification_sent(
        self,
        user_id: str,
        goal_id: str,
        message: str,
        now_ts: Optional[float] = None
    ) -> None:
        """Records notification in sent history for user."""
        now = now_ts if now_ts is not None else time.time()
        if user_id not in self._sent_notifications_history:
            self._sent_notifications_history[user_id] = []

        words = self._extract_words(message)
        self._sent_notifications_history[user_id].append((now, goal_id, words))
