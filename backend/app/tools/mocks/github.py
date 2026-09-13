"""
Mock GitHub Tool for Testing & Development.
"""

from typing import Dict, Any, Optional
from app.tools.base import BaseTool, ToolMetadata, ImpactLevel
from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolExecutionResult

class MockGitHubGetRecentActivityTool(BaseTool):
    """
    Mock GitHub Activity Tool (LOW Impact).
    Retrieves user activity events (commits, PRs).
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="github.get_recent_activity",
            description="Retrieves recent public/private commit activity for a GitHub user.",
            input_schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["username"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "activity": {"type": "array"}
                }
            },
            requires_authorization=False,
            requires_confirmation=False,
            impact_level=ImpactLevel.LOW,
            reversible=True,
            external_side_effect=False
        )

    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolExecutionResult:
        username = arguments.get("username")
        limit = arguments.get("limit", 5)

        return ToolExecutionResult(
            tool_name=self.metadata.name,
            status="success",
            result_data={
                "status": "ok",
                "username": username,
                "activity": [
                    {
                        "event_type": "PushEvent",
                        "repo": "jarvix/backend",
                        "commit_hash": "a1b2c3d4",
                        "message": "Implement Persistent Database & Tiered Memory System",
                        "timestamp": "2026-09-09T22:30:00Z"
                    },
                    {
                        "event_type": "PullRequestEvent",
                        "repo": "jarvix/backend",
                        "action": "opened",
                        "title": "Add Tool Registry and Executor Pipeline",
                        "timestamp": "2026-09-09T23:00:00Z"
                    }
                ][:limit]
            }
        )
