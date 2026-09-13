"""
Mock Observation Test Fixtures (Scenarios A through G).
"""

from datetime import datetime
from typing import List
from app.proactive.models import Observation

class ScenarioFixtures:
    # Scenario A: Relevant observation
    RELEVANT_GENAI_OBSERVATION = Observation(
        observation_id="obs_genai_001",
        source="mock_tech_rss",
        source_type="rss",
        title="Generative AI & LLM Fine-Tuning Masterclass",
        summary="A newly published practical guide covering PyTorch transformers and LoRA fine-tuning.",
        url="https://ai.example.com/masterclass",
        metadata={"category": "AI/ML", "priority": "HIGH"}
    )

    # Scenario B: Irrelevant observation
    IRRELEVANT_SPORTS_OBSERVATION = Observation(
        observation_id="obs_sports_001",
        source="mock_news_rss",
        source_type="rss",
        title="Weekend Tennis Final Highlights",
        summary="Scores and match statistics for national tennis finals.",
        url="https://news.example.com/sports",
        metadata={"category": "Sports"}
    )

    # Scenario D: Duplicate observation
    DUPLICATE_GENAI_OBSERVATION = Observation(
        observation_id="obs_genai_001", # Identical observation_id
        source="mock_tech_rss",
        source_type="rss",
        title="Generative AI & LLM Fine-Tuning Masterclass",
        summary="A newly published practical guide covering PyTorch transformers and LoRA fine-tuning.",
        url="https://ai.example.com/masterclass"
    )

    # Scenario E: Observation matching multiple goals (Generative AI + Career Goal)
    MULTI_GOAL_OBSERVATION = Observation(
        observation_id="obs_multi_001",
        source="mock_github",
        source_type="github",
        title="Open-Source GenAI Job & Project Opportunity",
        summary="High-priority project seeking contributors for PyTorch LLM deployment.",
        url="https://github.example.com/jobs/genai",
        metadata={"category": "Engineering"}
    )

    # Scenario G: High-Impact Action observation (Calendar event creation suggestion)
    HIGH_IMPACT_CALENDAR_OBSERVATION = Observation(
        observation_id="obs_high_001",
        source="mock_calendar",
        source_type="calendar",
        title="Reschedule Project Review Meeting",
        summary="Conflict detected in your calendar. Suggesting rescheduling project review meeting.",
        url="https://calendar.example.com/reschedule",
        metadata={"action_type": "create_calendar_event", "external_visible": True}
    )

def get_mock_test_observations() -> List[Observation]:
    return [
        ScenarioFixtures.RELEVANT_GENAI_OBSERVATION,
        ScenarioFixtures.IRRELEVANT_SPORTS_OBSERVATION,
        ScenarioFixtures.MULTI_GOAL_OBSERVATION,
        ScenarioFixtures.HIGH_IMPACT_CALENDAR_OBSERVATION
    ]
