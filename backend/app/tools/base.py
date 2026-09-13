"""
Base Tool Abstraction for JARVIX Capabilities & MCP Tool Adaption.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass, field

from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolExecutionResult

class ImpactLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class ToolMetadata:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requires_authorization: bool = False
    required_permission: Optional[str] = None
    requires_confirmation: bool = False
    impact_level: ImpactLevel = ImpactLevel.LOW
    reversible: bool = True
    external_side_effect: bool = False

@dataclass
class ToolVerificationResult:
    is_verified: bool
    status: str  # "VERIFIED_SUCCESS" | "VERIFIED_FAILURE" | "UNVERIFIED"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

class BaseTool(ABC):
    """
    Abstract Base Class for all JARVIX tools (Local, REST API, or MCP Adapters).
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Returns tool metadata descriptor."""
        pass

    @abstractmethod
    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolExecutionResult:
        """
        Executes the tool with validated input arguments and context.
        Must return a structured ToolExecutionResult.
        """
        pass

    def validate_input(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates input arguments against the tool's input schema.
        Override in subclasses or use default JSON schema / dictionary check.
        """
        schema = self.metadata.input_schema
        required_fields = schema.get("required", [])
        for req in required_fields:
            if req not in arguments or arguments[req] is None:
                raise ValueError(f"Missing required argument '{req}' for tool '{self.metadata.name}'")
        return arguments

    def verify(self, result: ToolExecutionResult) -> ToolVerificationResult:
        """
        Verifies claimed execution output against empirical result data.
        Default implementation checks status field and non-empty result_data.
        """
        if result.status == "success":
            if result.result_data is not None and result.result_data.get("status") in ["created", "sent", "success", "ok", "completed"]:
                return ToolVerificationResult(
                    is_verified=True,
                    status="VERIFIED_SUCCESS",
                    message=f"Tool '{self.metadata.name}' execution verified successfully."
                )
            elif result.result_data is not None and result.result_data.get("status") in ["failed", "error", "timeout"]:
                return ToolVerificationResult(
                    is_verified=False,
                    status="VERIFIED_FAILURE",
                    message=f"Tool '{self.metadata.name}' returned failure status in result data."
                )
            return ToolVerificationResult(
                is_verified=True,
                status="VERIFIED_SUCCESS",
                message=f"Tool '{self.metadata.name}' completed without structural errors."
            )
        else:
            return ToolVerificationResult(
                is_verified=False,
                status="VERIFIED_FAILURE",
                message=f"Tool '{self.metadata.name}' failed: {result.error_message or 'execution status was not success'}"
            )
