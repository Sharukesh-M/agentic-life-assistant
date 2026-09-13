"""
Tool Result Verifier Module.
Verifies claimed execution outcomes against empirical tool output data.
Prevents false-success claims and catches silent execution failures.
"""

from typing import Dict, Any, Optional
from app.tools.base import BaseTool, ToolVerificationResult
from app.schemas.tool_use import ToolExecutionResult
from app.tools.errors import ToolVerificationError

class ToolVerifier:
    """
    Validates tool execution results for truthfulness and empirical correctness.
    """

    @staticmethod
    def verify_execution_result(
        tool: BaseTool,
        result: ToolExecutionResult
    ) -> ToolVerificationResult:
        """
        Runs empirical verification on tool result data.
        Raises ToolVerificationError if false-success or structural contradiction detected.
        """
        # 1. Reject if tool execution status was explicitly not success
        if result.status != "success":
            verification = ToolVerificationResult(
                is_verified=False,
                status="VERIFIED_FAILURE",
                message=f"Tool '{result.tool_name}' failed execution: {result.error_message or 'unknown error'}"
            )
            return verification

        # 2. Delegate to tool custom verifier if defined
        verification = tool.verify(result)
        if not verification.is_verified:
            return verification

        # 3. Structural verification of result data
        if result.result_data is None:
            return ToolVerificationResult(
                is_verified=False,
                status="VERIFIED_FAILURE",
                message=f"Tool '{result.tool_name}' returned null result_data despite claiming success."
            )

        # Check for embedded failure/error indicators in result payload
        result_payload = result.result_data
        if result_payload.get("status") in ["failed", "error", "timeout", "unauthorized"]:
            return ToolVerificationResult(
                is_verified=False,
                status="VERIFIED_FAILURE",
                message=f"False-Success Blocked: Tool payload status indicates '{result_payload.get('status')}'."
            )

        return ToolVerificationResult(
            is_verified=True,
            status="VERIFIED_SUCCESS",
            message=f"Tool '{result.tool_name}' empirical result verified."
        )
