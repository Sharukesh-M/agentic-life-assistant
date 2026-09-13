"""
Mock Notification Tool for Testing & Development.
"""

import uuid
from typing import Dict, Any, Optional
from app.tools.base import BaseTool, ToolMetadata, ImpactLevel
from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolExecutionResult

class MockNotificationSendTool(BaseTool):
    """
    Mock Device / System Notification Sending Tool (HIGH Impact).
    Sends notifications to user devices. Requires authorization and confirmation.
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="notifications.send",
            description="Sends an alert/notification to user device. High impact communication side-effect.",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "priority": {"type": "string"},
                    "recipient": {"type": "string"}
                },
                "required": ["message"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "notification_id": {"type": "string"},
                    "status": {"type": "string"}
                }
            },
            requires_authorization=True,
            required_permission="notifications_send",
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
        # Simulation flag
        sim_mode = arguments.get("simulate", "success")
        if sim_mode == "failure":
            return ToolExecutionResult(
                tool_name=self.metadata.name,
                status="failure",
                result_data={"status": "failed"},
                error_message="Push Notification Service unreachable."
            )

        notification_id = f"notif_{uuid.uuid4().hex[:8]}"
        return ToolExecutionResult(
            tool_name=self.metadata.name,
            status="success",
            result_data={
                "notification_id": notification_id,
                "message": arguments.get("message"),
                "priority": arguments.get("priority", "MEDIUM"),
                "status": "sent"
            }
        )
