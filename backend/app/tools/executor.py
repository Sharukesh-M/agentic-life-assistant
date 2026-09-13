"""
Tool Executor Module for Safe, Authorized, and Verified Tool Execution.
"""

import time
import logging
from typing import Dict, Any, Optional
from app.tools.registry import ToolRegistry
from app.tools.context import ToolExecutionContext
from app.tools.authorization import ToolAuthorizationEngine
from app.tools.verifier import ToolVerifier
from app.schemas.tool_use import ToolCallRequest, ToolExecutionResult
from app.tools.errors import (
    ToolNotFoundError,
    ToolAuthorizationError,
    ToolConfirmationRequiredError,
    ToolValidationError,
    ToolVerificationError
)

logger = logging.getLogger("jarvix.tools.executor")

class ToolExecutor:
    """
    Main Execution Pipeline Manager for JARVIX Tools.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None, decision_engine: Optional[Any] = None):
        self.registry = registry or ToolRegistry.get_instance()
        self.auth_engine = ToolAuthorizationEngine()
        if decision_engine is None:
            from app.agent.decision_engine import DecisionEngine
            self.decision_engine = DecisionEngine()
        else:
            self.decision_engine = decision_engine
        self.verifier = ToolVerifier()

    def execute_tool(
        self,
        request: ToolCallRequest,
        context: Optional[ToolExecutionContext] = None
    ) -> ToolExecutionResult:
        """
        Full Tool Execution Pipeline:
        1. Discovery -> 2. Input Validation -> 3. Authorization -> 4. Confirmation -> 5. Execution -> 6. Result Verification
        """
        start_time = time.time()
        tool_name = request.tool_name
        arguments = request.arguments or {}

        if context is None:
            context = ToolExecutionContext()

        # Step 1: Tool Discovery
        if not self.registry.has(tool_name):
            logger.warning(f"[Tool Execution] Tool '{tool_name}' not found in registry.")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="failure",
                error_message=f"Tool '{tool_name}' is not registered in the tool catalog.",
                execution_time_seconds=time.time() - start_time
            )

        tool = self.registry.get(tool_name)
        metadata = tool.metadata

        # Step 2: Input Argument Validation
        try:
            validated_args = tool.validate_input(arguments)
        except Exception as e:
            logger.warning(f"[Tool Validation Error] {e}")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="failure",
                error_message=f"Input validation failed: {str(e)}",
                execution_time_seconds=time.time() - start_time
            )

        # Step 3: Application-Level Authorization Check
        is_auth, auth_reason = self.auth_engine.is_authorized(tool, context)
        if not is_auth:
            logger.warning(f"[Tool Authorization Block] {auth_reason}")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="unauthorized",
                error_message=f"Authorization Blocked: {auth_reason}",
                execution_time_seconds=time.time() - start_time
            )

        # Step 4: High-Impact Confirmation Check
        is_reversible = self.decision_engine.is_action_reversible(tool_name, {"external_visible": metadata.external_side_effect})
        requires_confirm = metadata.requires_confirmation or not is_reversible

        if requires_confirm and not context.confirmed_by_user:
            logger.info(f"[Tool Confirmation Required] Tool '{tool_name}' requires explicit user confirmation.")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="failure",
                error_message=f"Confirmation Required: Action '{tool_name}' is high-impact and requires explicit user confirmation.",
                execution_time_seconds=time.time() - start_time
            )

        # Step 5: Execute Tool
        try:
            raw_result = tool.execute(validated_args, context)
        except Exception as e:
            logger.error(f"[Tool Execution Runtime Error] '{tool_name}': {str(e)}")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="failure",
                error_message=f"Runtime error during tool execution: {str(e)}",
                execution_time_seconds=time.time() - start_time
            )

        # Step 6: Empirical Verification
        verification = self.verifier.verify_execution_result(tool, raw_result)
        if not verification.is_verified:
            logger.warning(f"[Tool Verification Block] '{tool_name}': {verification.message}")
            return ToolExecutionResult(
                tool_name=tool_name,
                status="failure",
                error_message=f"Verification Failed: {verification.message}",
                execution_time_seconds=time.time() - start_time
            )

        raw_result.execution_time_seconds = time.time() - start_time
        return raw_result
