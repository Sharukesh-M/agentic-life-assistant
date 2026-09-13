"""
JARVIX Tool Capability Architecture Package.
Centralized Tool Registry, Authorization Engine, Tool Executor Pipeline, Verifier, and MCP Adapters.
"""

from app.tools.base import BaseTool, ToolMetadata, ImpactLevel, ToolVerificationResult
from app.tools.context import ToolExecutionContext
from app.tools.errors import (
    ToolError,
    ToolNotFoundError,
    ToolAuthorizationError,
    ToolConfirmationRequiredError,
    ToolValidationError,
    ToolExecutionError,
    ToolVerificationError
)
from app.tools.registry import ToolRegistry
from app.tools.authorization import ToolAuthorizationEngine
from app.tools.verifier import ToolVerifier
from app.tools.executor import ToolExecutor
from app.tools.mocks import register_mock_tools
from app.tools.adapters.mcp_adapter import MCPToolAdapter

__all__ = [
    "BaseTool",
    "ToolMetadata",
    "ImpactLevel",
    "ToolVerificationResult",
    "ToolExecutionContext",
    "ToolError",
    "ToolNotFoundError",
    "ToolAuthorizationError",
    "ToolConfirmationRequiredError",
    "ToolValidationError",
    "ToolExecutionError",
    "ToolVerificationError",
    "ToolRegistry",
    "ToolAuthorizationEngine",
    "ToolVerifier",
    "ToolExecutor",
    "register_mock_tools",
    "MCPToolAdapter"
]
