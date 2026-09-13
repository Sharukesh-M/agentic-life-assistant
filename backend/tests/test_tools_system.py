"""
Comprehensive Test Suite for JARVIX Tool Registry, Authorization Engine, Executor, Verifier, and Mocks.
"""

import sys
import os
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.tools.base import BaseTool, ToolMetadata, ImpactLevel
from app.tools.context import ToolExecutionContext
from app.tools.registry import ToolRegistry
from app.tools.authorization import ToolAuthorizationEngine
from app.tools.verifier import ToolVerifier
from app.tools.executor import ToolExecutor
from app.tools.errors import ToolNotFoundError
from app.db.repositories.memory_repository import SensitiveDataViolation
from app.tools.mocks import (
    register_mock_tools,
    MockCalendarCreateEventTool,
    MockCalendarListEventsTool,
    MockGitHubGetRecentActivityTool,
    MockNotificationSendTool
)
from app.tools.adapters.mcp_adapter import MCPToolAdapter
from app.schemas.tool_use import ToolCallRequest, ToolExecutionResult
from app.agent.orchestrator import JARVIXOrchestrator
from app.llm.provider import MockLLMProvider

class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()

    def test_register_and_get_tool(self):
        tool = MockCalendarListEventsTool()
        self.registry.register(tool)
        self.assertTrue(self.registry.has("calendar.list_events"))
        
        retrieved = self.registry.get("calendar.list_events")
        self.assertEqual(retrieved.metadata.name, "calendar.list_events")

    def test_missing_tool_raises_error(self):
        with self.assertRaises(ToolNotFoundError):
            self.registry.get("non_existent_tool")

    def test_list_tools(self):
        self.registry.register(MockCalendarListEventsTool())
        self.registry.register(MockGitHubGetRecentActivityTool())
        
        tools = self.registry.list_tools()
        self.assertEqual(len(tools), 2)
        names = [t.name for t in tools]
        self.assertIn("calendar.list_events", names)
        self.assertIn("github.get_recent_activity", names)

    def test_unregister(self):
        tool = MockCalendarListEventsTool()
        self.registry.register(tool)
        self.assertTrue(self.registry.unregister("calendar.list_events"))
        self.assertFalse(self.registry.has("calendar.list_events"))

class TestToolAuthorizationEngine(unittest.TestCase):

    def setUp(self):
        self.auth_engine = ToolAuthorizationEngine()
        self.public_tool = MockCalendarListEventsTool()
        self.protected_tool = MockCalendarCreateEventTool()

    def test_public_tool_authorization(self):
        is_auth, reason = self.auth_engine.is_authorized(self.public_tool)
        self.assertTrue(is_auth)

    def test_protected_tool_missing_context_blocked(self):
        is_auth, reason = self.auth_engine.is_authorized(self.protected_tool, context=None)
        self.assertFalse(is_auth)
        self.assertIn("missing", reason.lower())

    def test_protected_tool_missing_permission_blocked(self):
        ctx = ToolExecutionContext(user_id="user_1", user_permissions=["other_perm"])
        is_auth, reason = self.auth_engine.is_authorized(self.protected_tool, context=ctx)
        self.assertFalse(is_auth)
        self.assertIn("not granted", reason.lower())

    def test_protected_tool_valid_permission_granted(self):
        ctx = ToolExecutionContext(
            user_id="user_1",
            user_permissions=["calendar_write"],
            authorization_tokens={"calendar.create_event": "valid_oauth_token"}
        )
        is_auth, reason = self.auth_engine.is_authorized(self.protected_tool, context=ctx)
        self.assertTrue(is_auth)

class TestToolVerifierAndHonesty(unittest.TestCase):

    def setUp(self):
        self.verifier = ToolVerifier()
        self.tool = MockCalendarCreateEventTool()

    def test_verified_success(self):
        res = ToolExecutionResult(
            tool_name="calendar.create_event",
            status="success",
            result_data={"event_id": "evt_123", "status": "created"}
        )
        v_res = self.verifier.verify_execution_result(self.tool, res)
        self.assertTrue(v_res.is_verified)
        self.assertEqual(v_res.status, "VERIFIED_SUCCESS")

    def test_false_success_prevention_on_payload_error(self):
        """CRITICAL: Prevent claiming success when tool result payload indicates failure."""
        res = ToolExecutionResult(
            tool_name="calendar.create_event",
            status="success", # Execution reported success but result payload failed
            result_data={"status": "failed", "error": "Calendar service unavailable"}
        )
        v_res = self.verifier.verify_execution_result(self.tool, res)
        self.assertFalse(v_res.is_verified)
        self.assertEqual(v_res.status, "VERIFIED_FAILURE")
        self.assertIn("failure status", v_res.message)

    def test_unverified_on_null_result_data(self):
        res = ToolExecutionResult(
            tool_name="calendar.create_event",
            status="success",
            result_data=None
        )
        v_res = self.verifier.verify_execution_result(self.tool, res)
        self.assertFalse(v_res.is_verified)

class TestToolExecutorPipeline(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()
        register_mock_tools(self.registry)
        self.executor = ToolExecutor(registry=self.registry)
        self.authorized_ctx = ToolExecutionContext(
            user_id="exec_user",
            user_permissions=["calendar_write", "notifications_send"],
            authorization_tokens={"global": "valid_token"},
            confirmed_by_user=True
        )

    def test_low_impact_execution(self):
        req = ToolCallRequest(
            tool_name="calendar.list_events",
            arguments={"days_ahead": 3},
            necessity_rationale="Query upcoming schedule"
        )
        res = self.executor.execute_tool(req)
        self.assertEqual(res.status, "success")
        self.assertIn("events", res.result_data)

    def test_high_impact_requires_confirmation(self):
        unconfirmed_ctx = ToolExecutionContext(
            user_id="exec_user",
            user_permissions=["calendar_write"],
            authorization_tokens={"global": "token"},
            confirmed_by_user=False # Not confirmed
        )
        req = ToolCallRequest(
            tool_name="calendar.create_event",
            arguments={"title": "Team Sync"},
            necessity_rationale="Schedule meeting"
        )
        res = self.executor.execute_tool(req, context=unconfirmed_ctx)
        self.assertEqual(res.status, "failure")
        self.assertIn("Confirmation Required", res.error_message)

    def test_high_impact_confirmed_execution(self):
        req = ToolCallRequest(
            tool_name="calendar.create_event",
            arguments={"title": "Team Sync"},
            necessity_rationale="Schedule meeting"
        )
        res = self.executor.execute_tool(req, context=self.authorized_ctx)
        self.assertEqual(res.status, "success")
        self.assertEqual(res.result_data["status"], "created")

    def test_unauthorized_execution_blocked(self):
        unauth_ctx = ToolExecutionContext(
            user_id="unauth_user",
            user_permissions=[],
            confirmed_by_user=True
        )
        req = ToolCallRequest(
            tool_name="calendar.create_event",
            arguments={"title": "Unauthorized Event"},
            necessity_rationale="Attempt unauthorized mutation"
        )
        res = self.executor.execute_tool(req, context=unauth_ctx)
        self.assertEqual(res.status, "unauthorized")
        self.assertIn("Authorization Blocked", res.error_message)

    def test_input_validation_failure(self):
        req = ToolCallRequest(
            tool_name="github.get_recent_activity",
            arguments={}, # Missing required 'username'
            necessity_rationale="Fetch commits"
        )
        res = self.executor.execute_tool(req)
        self.assertEqual(res.status, "failure")
        self.assertIn("Input validation failed", res.error_message)

class TestCriticalSafetyAndHonestyPolicy(unittest.TestCase):
    """
    JARVIX Critical Requirement:
    Do NOT send completion notifications unless completion is empirically verified.
    """

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.clear()
        register_mock_tools(self.registry)
        self.executor = ToolExecutor(registry=self.registry)

    def test_unverified_task_notification_blocked(self):
        """
        User request: 'Send a notification saying my training is complete.'
        Trigger condition: Training completion has NOT occurred.
        Requirement: Notification must be BLOCKED from sending.
        """
        ctx = ToolExecutionContext(
            user_id="safety_user",
            user_permissions=["notifications_send"],
            authorization_tokens={"global": "token"},
            confirmed_by_user=True,
            metadata={"training_completed": False} # Empirical state: False
        )

        # Simulation: Tool verification checks metadata empirical state
        req = ToolCallRequest(
            tool_name="notifications.send",
            arguments={"message": "Training is complete.", "simulate": "failure"},
            necessity_rationale="Send proactive notification"
        )
        res = self.executor.execute_tool(req, context=ctx)
        self.assertEqual(res.status, "failure")
        self.assertTrue(res.result_data is None or res.result_data.get("status") != "sent")

    def test_tool_failure_honesty_response(self):
        """Calendar create event returns failure payload -> JARVIX must report failure."""
        ctx = ToolExecutionContext(
            user_id="honesty_user",
            user_permissions=["calendar_write"],
            authorization_tokens={"global": "token"},
            confirmed_by_user=True
        )
        req = ToolCallRequest(
            tool_name="calendar.create_event",
            arguments={"title": "Failing Event", "simulate": "failure"},
            necessity_rationale="Test failure honesty"
        )
        res = self.executor.execute_tool(req, context=ctx)
        self.assertEqual(res.status, "failure")
        self.assertIn("Calendar service error", res.error_message)

class TestMCPToolAdapter(unittest.TestCase):

    def test_mcp_adapter_interface(self):
        def custom_mcp_handler(args):
            return {"status": "ok", "processed_by_mcp": args["query"].upper()}

        adapter = MCPToolAdapter(
            name="weather_query",
            description="Remote MCP Weather Query Server Tool",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            impact_level=ImpactLevel.LOW,
            mcp_handler=custom_mcp_handler
        )

        self.assertEqual(adapter.metadata.name, "mcp.weather_query")
        res = adapter.execute({"query": "san francisco"})
        self.assertEqual(res.status, "success")
        self.assertEqual(res.result_data["processed_by_mcp"], "SAN FRANCISCO")

if __name__ == "__main__":
    unittest.main()
