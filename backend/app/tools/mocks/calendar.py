"""
Mock Calendar Tools for Testing & Development.
"""

import uuid
import time
from typing import Dict, Any, Optional
from app.tools.base import BaseTool, ToolMetadata, ImpactLevel
from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolExecutionResult

class MockCalendarCreateEventTool(BaseTool):
    """
    Mock Calendar Event Creation Tool (HIGH Impact).
    Requires authorization & confirmation.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar.create_event",
            description="Creates a new calendar event. High impact external side effect.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string"},
                    "duration_minutes": {"type": "integer"}
                },
                "required": ["title"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            requires_authorization=True,
            required_permission="calendar_write",
            requires_confirmation=True,
            impact_level=ImpactLevel.HIGH,
            reversible=False,
            external_side_effect=True
        )

    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolExecutionResult:
        # Simulation flags via arguments
        sim_mode = arguments.get("simulate", "success")

        if sim_mode == "timeout":
            time.sleep(0.01)
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                status="failure",
                error_message="Simulated Calendar API request timeout."
            )
        elif sim_mode == "failure":
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                status="failure",
                result_data={"status": "failed"},
                error_message="Calendar service error 500."
            )

        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        return ToolExecutionResult(
            tool_name=self.metadata.name,
            status="success",
            result_data={
                "event_id": event_id,
                "title": arguments.get("title"),
                "start_time": arguments.get("start_time", "2026-09-10T10:00:00Z"),
                "duration_minutes": arguments.get("duration_minutes", 30),
                "status": "created"
            }
        )

class MockCalendarListEventsTool(BaseTool):
    """
    Mock Calendar Event Retrieval Tool (LOW Impact).
    Read-only query, no external mutation.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calendar.list_events",
            description="Retrieves upcoming calendar events. Low impact read-only query.",
            input_schema={
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "events": {"type": "array"}
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
        days = arguments.get("days_ahead", 7)
        return ToolExecutionResult(
            tool_name=self.metadata.name,
            status="success",
            result_data={
                "status": "ok",
                "days_ahead": days,
                "events": [
                    {
                        "event_id": "evt_mock_1",
                        "title": "Generative AI Study Session",
                        "start_time": "2026-09-10T14:00:00Z",
                        "duration_minutes": 60
                    },
                    {
                        "event_id": "evt_mock_2",
                        "title": "JARVIX System Architecture Review",
                        "start_time": "2026-09-11T16:00:00Z",
                        "duration_minutes": 45
                    }
                ]
            }
        )
