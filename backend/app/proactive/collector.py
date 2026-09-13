"""
Observation Collector Architecture & Mock Source Registries.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional, Callable
from app.proactive.models import Observation

class BaseObservationCollector(ABC):
    """Abstract Base Class for Observation Collectors."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        pass

    @abstractmethod
    def collect(
        self,
        user_id: str,
        last_checked: Optional[datetime] = None
    ) -> List[Observation]:
        """Collects fresh observations for specified user."""
        pass

class CollectorRegistry:
    """Registry managing active observation collectors."""

    def __init__(self):
        self._collectors: Dict[str, BaseObservationCollector] = {}

    def register(self, collector: BaseObservationCollector) -> None:
        self._collectors[collector.source_name] = collector

    def list_collectors(self) -> List[BaseObservationCollector]:
        return list(self._collectors.values())

    def collect_all(
        self,
        user_id: str,
        last_checked: Optional[datetime] = None
    ) -> List[Observation]:
        """Invokes all registered collectors and aggregates observations safely."""
        all_obs: List[Observation] = []
        for name, collector in self._collectors.items():
            try:
                obs = collector.collect(user_id, last_checked)
                all_obs.extend(obs)
            except Exception as e:
                print(f"[Observation Collector Error] Collector '{name}' failed: {e}")
        return all_obs

class MockCalendarObservationCollector(BaseObservationCollector):
    """MOCK Calendar Event Collector."""
    @property
    def source_name(self) -> str:
        return "mock_calendar_collector"

    @property
    def source_type(self) -> str:
        return "calendar"

    def collect(self, user_id: str, last_checked: Optional[datetime] = None) -> List[Observation]:
        return [
            Observation(
                observation_id="obs_cal_001",
                source="mock_calendar",
                source_type="calendar",
                title="Generative AI Workshop & Hackathon Announced",
                summary="A 2-day hands-on PyTorch & LLM Fine-Tuning Workshop scheduled for this weekend.",
                url="https://calendar.example.com/events/genai-workshop",
                metadata={"category": "Workshop", "suggested_action": "reschedule_task"}
            )
        ]

class MockGitHubObservationCollector(BaseObservationCollector):
    """MOCK GitHub Commit / Repository Activity Collector."""
    @property
    def source_name(self) -> str:
        return "mock_github_collector"

    @property
    def source_type(self) -> str:
        return "github"

    def collect(self, user_id: str, last_checked: Optional[datetime] = None) -> List[Observation]:
        return [
            Observation(
                observation_id="obs_gh_001",
                source="mock_github",
                source_type="github",
                title="New Open-Source Transformer Optimization Library Released",
                summary="Repository release v2.0 with 3x speedup for PyTorch attention kernels.",
                url="https://github.example.com/fast-attention/releases/tag/v2.0",
                metadata={"repo": "fast-attention", "stars": 1200}
            )
        ]

class MockRSSObservationCollector(BaseObservationCollector):
    """MOCK RSS / Tech News Collector."""
    @property
    def source_name(self) -> str:
        return "mock_rss_collector"

    @property
    def source_type(self) -> str:
        return "rss"

    def collect(self, user_id: str, last_checked: Optional[datetime] = None) -> List[Observation]:
        return [
            Observation(
                observation_id="obs_rss_001",
                source="mock_rss",
                source_type="rss",
                title="Unrelated Sports Tournament Results",
                summary="Final scores for weekend national tennis championships.",
                url="https://news.example.com/sports/tennis",
                metadata={"category": "Sports"}
            )
        ]
