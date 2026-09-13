"""
Goal-Event Correlation Pipeline.
Evaluates semantic relevance between fresh observations and active user goals using Goal Management prompts & calibration anchors.
"""

import json
import re
from typing import List, Dict, Any, Optional
from app.proactive.models import Observation
from app.schemas.goals import EventMatchItem, GoalEventCorrelationOutput, GoalRecord
from app.agent.prompt_loader import assemble_agent_prompt
from app.llm.base import BaseLLMProvider
from app.llm.provider import get_llm_provider

class GoalEventCorrelator:
    """
    Evaluates semantic correlation between incoming observations and user active goals.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    def correlate(
        self,
        observation: Observation,
        active_goals: List[Any]
    ) -> GoalEventCorrelationOutput:
        """
        Correlates observation against list of active goals.
        Returns GoalEventCorrelationOutput with matches and relevance scores.
        """
        if not active_goals:
            return GoalEventCorrelationOutput(matches=[], no_relevant_goals=True)

        # Build goal descriptions for LLM / Heuristic scoring
        goals_data = []
        for g in active_goals:
            g_dict = {
                "goal_id": getattr(g, "goal_id", g.get("goal_id") if isinstance(g, dict) else "unknown"),
                "title": getattr(g, "title", g.get("title") if isinstance(g, dict) else ""),
                "category": getattr(g, "category", g.get("category") if isinstance(g, dict) else "General"),
                "priority": getattr(g, "priority", g.get("priority") if isinstance(g, dict) else "MEDIUM"),
                "description": getattr(g, "description", g.get("description") if isinstance(g, dict) else "")
            }
            goals_data.append(g_dict)

        system_prompt = assemble_agent_prompt("goals/goal_management.md")
        user_prompt = f"""
INCOMING_EXTERNAL_OBSERVATION:
- Title: {observation.title}
- Source: {observation.source} ({observation.source_type})
- Summary: {observation.summary}
- Metadata: {json.dumps(observation.metadata)}

ACTIVE_USER_GOALS:
{json.dumps(goals_data, indent=2)}
"""

        # Call LLM for semantic correlation scoring
        llm_resp = self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format_json=True
        )

        if llm_resp.success and llm_resp.parsed_json:
            try:
                matches_raw = llm_resp.parsed_json.get("matches", [])
                items = [EventMatchItem(**m) for m in matches_raw]
                return GoalEventCorrelationOutput(
                    matches=items,
                    no_relevant_goals=len(items) == 0
                )
            except Exception:
                pass

        # Fallback Semantic / Keyword Heuristic Correlation Scorer
        return self._heuristic_correlate(observation, goals_data)

    def _heuristic_correlate(
        self,
        observation: Observation,
        goals_data: List[Dict[str, Any]]
    ) -> GoalEventCorrelationOutput:
        """
        Fallback heuristic correlation engine using word overlap & anchor calibration.
        """
        matches: List[EventMatchItem] = []
        obs_text = f"{observation.title} {observation.summary}".lower()
        obs_words = set(re.findall(r'\w+', obs_text))

        for g in goals_data:
            g_title = g["title"].lower()
            g_desc = (g.get("description") or "").lower()
            g_cat = g.get("category", "").lower()
            g_words = set(re.findall(r'\w+', f"{g_title} {g_desc} {g_cat}"))

            # Calculate word overlap
            overlap = len(obs_words.intersection(g_words))
            if overlap == 0:
                continue

            # Calibration anchors:
            # - High topical match + HIGH priority -> 0.85+
            # - Category-only match -> 0.40
            # - Multi-word match -> 0.70+
            base_score = min(0.35 + (overlap * 0.15), 0.90)
            if g["priority"] == "HIGH":
                base_score = min(base_score + 0.10, 0.95)

            # Check for specific action suggestions from observation metadata
            s_action = observation.metadata.get("suggested_action", "recommend")

            match_item = EventMatchItem(
                goal_id=g["goal_id"],
                relevance_score=round(base_score, 2),
                goal_priority=g["priority"],
                reason=f"Observation '{observation.title}' matches goal topic '{g['title']}'.",
                suggested_action=s_action
            )
            matches.append(match_item)

        # Sort matches by relevance score descending
        matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return GoalEventCorrelationOutput(
            matches=matches,
            no_relevant_goals=len(matches) == 0
        )
