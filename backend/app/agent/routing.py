"""
Capability Routing Dispatcher for JARVIX Orchestrator.
"""

from typing import List, Dict, Any

SUPPORTED_CAPABILITIES = {
    "Goal Management": "app/prompts/goals/goal_management.md",
    "Planning": "app/prompts/planning/planning_agent.md",
    "Memory": "app/prompts/memory/memory_agent.md",
    "Orchestration": "app/prompts/orchestration/orchestrator.md",
    "Proactive Monitor": "app/prompts/proactive/proactive_monitor.md",
    "Tool Use": "app/prompts/tool_use/tool_use.md",
    "General Conversation": None
}

class RoutingDispatcher:
    @staticmethod
    def get_prompt_for_capability(capability: str) -> str:
        return SUPPORTED_CAPABILITIES.get(capability, None)

    @staticmethod
    def list_capabilities() -> List[str]:
        return list(SUPPORTED_CAPABILITIES.keys())
