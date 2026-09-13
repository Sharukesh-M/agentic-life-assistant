"""
Comprehensive Test Suite for JARVIX Proactive Intelligence System.
Tests Goal-Event Correlation, Decision Engine, Quiet Hours Hard Gates, Deduplication, Safety Action Boundaries, Scheduler, and User Isolation.
"""

import sys
import os
import unittest
from datetime import datetime

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.proactive.models import (
    Observation,
    NotificationPreference,
    ProactiveCandidate,
    ProactiveCycleResult
)
from app.proactive.collector import (
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
from app.proactive.mocks.observations import ScenarioFixtures
from app.schemas.goals import EventMatchItem, GoalEventCorrelationOutput
from app.db.config import DBConfig
from app.db.session import init_db, get_session_factory
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.notification_repository import NotificationRepository
from app.db.repositories.agent_run_repository import AgentRunRepository
from app.llm.provider import MockLLMProvider

class TestGoalEventCorrelation(unittest.TestCase):

    def setUp(self):
        self.correlator = GoalEventCorrelator(llm_provider=MockLLMProvider())
        self.active_goals = [
            {
                "goal_id": "g_genai",
                "title": "Learn Generative AI in 30 Days",
                "category": "AI/ML",
                "priority": "HIGH",
                "description": "Master PyTorch LLM fine-tuning and transformers."
            },
            {
                "goal_id": "g_career",
                "title": "Advance Engineering Career",
                "category": "Career",
                "priority": "MEDIUM",
                "description": "Contribute to open-source PyTorch projects."
            }
        ]

    def test_scenario_a_relevant_correlation(self):
        """Scenario A: Relevant observation matches active goal with high relevance score."""
        obs = ScenarioFixtures.RELEVANT_GENAI_OBSERVATION
        corr = self.correlator.correlate(obs, self.active_goals)
        self.assertFalse(corr.no_relevant_goals)
        self.assertGreater(len(corr.matches), 0)
        top_match = corr.matches[0]
        self.assertEqual(top_match.goal_id, "g_genai")
        self.assertGreaterEqual(top_match.relevance_score, 0.70)

    def test_scenario_b_irrelevant_correlation(self):
        """Scenario B: Unrelated sports observation matches no goals."""
        obs = ScenarioFixtures.IRRELEVANT_SPORTS_OBSERVATION
        corr = self.correlator.correlate(obs, self.active_goals)
        self.assertTrue(corr.no_relevant_goals or len(corr.matches) == 0)

    def test_scenario_e_multiple_goals_correlation(self):
        """Scenario E: Observation relates to multiple active goals."""
        obs = ScenarioFixtures.MULTI_GOAL_OBSERVATION
        corr = self.correlator.correlate(obs, self.active_goals)
        self.assertFalse(corr.no_relevant_goals)
        matched_goal_ids = [m.goal_id for m in corr.matches]
        self.assertIn("g_genai", matched_goal_ids)
        self.assertIn("g_career", matched_goal_ids)

class TestNotificationPolicyAndQuietHours(unittest.TestCase):

    def setUp(self):
        self.decision_engine = ProactiveDecisionEngine()
        self.correlation = GoalEventCorrelationOutput(
            matches=[
                EventMatchItem(
                    goal_id="g_genai",
                    relevance_score=0.88,
                    goal_priority="HIGH",
                    reason="Topical match",
                    suggested_action="recommend"
                )
            ]
        )

    def test_scenario_c_quiet_hours_suppression(self):
        """Scenario C: Relevant observation evaluated during quiet hours MUST be suppressed."""
        pref = NotificationPreference(
            user_id="user_quiet",
            quiet_hours_enabled=True,
            quiet_hours_start=22,  # 10 PM
            quiet_hours_end=7     # 7 AM
        )
        # Evaluate at 23:00 (11 PM) - inside quiet hours
        candidate = self.decision_engine.evaluate_candidate(
            observation=ScenarioFixtures.RELEVANT_GENAI_OBSERVATION,
            correlation=self.correlation,
            preference=pref,
            current_hour=23
        )
        self.assertTrue(candidate.is_suppressed)
        self.assertEqual(candidate.decision, "ignore")
        self.assertIn("quiet hours", candidate.suppression_reason.lower())

    def test_daytime_notification_allowed(self):
        """Daytime evaluation (14:00 / 2 PM) outside quiet hours allows notification."""
        pref = NotificationPreference(
            user_id="user_day",
            quiet_hours_enabled=True,
            quiet_hours_start=22,
            quiet_hours_end=7
        )
        candidate = self.decision_engine.evaluate_candidate(
            observation=ScenarioFixtures.RELEVANT_GENAI_OBSERVATION,
            correlation=self.correlation,
            preference=pref,
            current_hour=14
        )
        self.assertFalse(candidate.is_suppressed)
        self.assertEqual(candidate.decision, "notify")

    def test_disabled_notifications_preference(self):
        """Frequency = NONE suppresses all notifications."""
        pref = NotificationPreference(user_id="user_off", frequency="NONE")
        candidate = self.decision_engine.evaluate_candidate(
            observation=ScenarioFixtures.RELEVANT_GENAI_OBSERVATION,
            correlation=self.correlation,
            preference=pref,
            current_hour=14
        )
        self.assertTrue(candidate.is_suppressed)

class TestDeduplication(unittest.TestCase):

    def setUp(self):
        self.dedup = ProactiveDeduplicator(deduplication_window_seconds=3600.0)

    def test_scenario_d_duplicate_observation_freshness(self):
        """Scenario D: Same observation_id processed twice is ignored on second check."""
        user_id = "user_dedup_1"
        obs_id = "obs_genai_001"

        self.assertFalse(self.dedup.is_observation_processed(user_id, obs_id))
        self.dedup.mark_observation_processed(user_id, obs_id)
        self.assertTrue(self.dedup.is_observation_processed(user_id, obs_id))

    def test_scenario_f_duplicate_notification_suppression(self):
        """Scenario F: Similar notification surfaced for same goal within window is suppressed."""
        user_id = "user_dedup_2"
        goal_id = "g_genai"
        msg = "Proactive Alert: Generative AI & LLM Fine-Tuning Masterclass released."

        # First alert is not duplicate
        self.assertFalse(self.dedup.is_duplicate_notification(user_id, goal_id, msg))
        self.dedup.mark_notification_sent(user_id, goal_id, msg)

        # Second similar alert for same goal IS duplicate
        msg_similar = "Proactive Alert: Generative AI LLM Fine-Tuning Masterclass available now."
        self.assertTrue(self.dedup.is_duplicate_notification(user_id, goal_id, msg_similar))

class TestSafetyAndActionBoundaries(unittest.TestCase):

    def setUp(self):
        self.decision_engine = ProactiveDecisionEngine()

    def test_scenario_g_high_impact_state_changing_action(self):
        """Scenario G: State-changing observation action requires confirmation and sets decision = 'ask_user'."""
        obs = ScenarioFixtures.HIGH_IMPACT_CALENDAR_OBSERVATION
        corr = GoalEventCorrelationOutput(
            matches=[
                EventMatchItem(
                    goal_id="g_genai",
                    relevance_score=0.85,
                    goal_priority="HIGH",
                    reason="Schedule conflict",
                    suggested_action="reschedule_task"
                )
            ]
        )
        pref = NotificationPreference(user_id="user_safety")
        candidate = self.decision_engine.evaluate_candidate(
            observation=obs,
            correlation=corr,
            preference=pref,
            current_hour=14
        )
        self.assertEqual(candidate.decision, "ask_user")
        self.assertTrue(candidate.requires_confirmation)
        self.assertIn("requires user confirmation", candidate.reason.lower())

class TestProactiveServiceIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DBConfig(database_url="sqlite:///:memory:")
        init_db(cls.config)
        cls.SessionFactory = get_session_factory(cls.config)

    def setUp(self):
        init_db(self.config)
        self.session = self.SessionFactory()
        self.user_id = "proactive_integration_user"
        
        # Populate DB with active goal
        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(
            goal_id="g_genai_db",
            user_id=self.user_id,
            title="Learn Generative AI in 30 Days",
            category="AI/ML",
            priority="HIGH"
        )
        self.service = ProactiveService(llm_provider=MockLLMProvider())

    def test_full_proactive_cycle_run(self):
        """Tests complete end-to-end proactive cycle with DB goal loading & notification persistence."""
        # Set daytime preference
        pref = NotificationPreference(user_id=self.user_id, quiet_hours_enabled=False)
        self.service.set_user_preference(pref)

        # Run cycle at 14:00 (2 PM)
        daytime = datetime(2026, 9, 10, 14, 0, 0)
        res = self.service.run_cycle(user_id=self.user_id, current_time=daytime, db_session=self.session)

        self.assertEqual(res.user_id, self.user_id)
        self.assertGreater(res.observations_collected, 0)
        self.assertGreater(res.notifications_sent, 0)

        # Verify notification was persisted in DB
        notif_repo = NotificationRepository(self.session)
        user_notifs = notif_repo.list_user_notifications(self.user_id)
        self.assertGreater(len(user_notifs), 0)

        # Verify agent run was logged in DB
        run_repo = AgentRunRepository(self.session)
        runs = run_repo.list_user_runs(self.user_id)
        self.assertGreater(len(runs), 0)

    def test_user_data_isolation(self):
        """Verify User A proactive check NEVER accesses or surfaces User B goals/notifications."""
        user_a = "proactive_user_a"
        user_b = "proactive_user_b"

        goal_repo = GoalRepository(self.session)
        goal_repo.create_goal(goal_id="g_a", user_id=user_a, title="User A Goal")
        goal_repo.create_goal(goal_id="g_b", user_id=user_b, title="User B Goal")

        daytime = datetime(2026, 9, 10, 14, 0, 0)
        res_a = self.service.run_cycle(user_id=user_a, current_time=daytime, db_session=self.session)
        
        for msg in res_a.surfaced_messages:
            self.assertNotEqual(msg.get("goal_id"), "g_b")

if __name__ == "__main__":
    unittest.main()
