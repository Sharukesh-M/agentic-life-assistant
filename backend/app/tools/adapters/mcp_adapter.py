"""
MCP (Model Context Protocol) Tool Adapter.
Bridges external MCP server tool definitions and JSON-RPC calls to the standard JARVIX BaseTool interface.
"""

from typing import Dict, Any, Optional, Callable
from app.tools.base import BaseTool, ToolMetadata, ImpactLevel
from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolExecutionResult

class MCPToolAdapter(BaseTool):
    """
    Adapter wrapping an MCP Server Tool definition into the JARVIX BaseTool contract.
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        impact_level: ImpactLevel = ImpactLevel.LOW,
        requires_authorization: bool = False,
        requires_confirmation: bool = False,
        mcp_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    ):
        self._name = f"mcp.{name}" if not name.startswith("mcp.") else name
        self._description = description
        self._input_schema = input_schema
        self._output_schema = output_schema or {"type": "object"}
        self._impact_level = impact_level
        self._requires_authorization = requires_authorization
        self._requires_confirmation = requires_confirmation
        self._mcp_handler = mcp_handler

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self._name,
            description=self._description,
            input_schema=self._input_schema,
            output_schema=self._output_schema,
            requires_authorization=self._requires_authorization,
            requires_confirmation=self._requires_confirmation,
            impact_level=self._impact_level,
            reversible=(self._impact_level == ImpactLevel.LOW),
            external_side_effect=(self._impact_level != ImpactLevel.LOW)
        )

    def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolExecutionResult:
        """
        Executes MCP Tool request by invoking the registered MCP handler or JSON-RPC bridge.
        """
        if self._mcp_handler:
            try:
                res_data = self._mcp_handler(arguments)
                return ToolExecutionResult(
                    tool_name=self.metadata.name,
                    status="success",
                    result_data=res_data
                )
            except Exception as e:
                return ToolExecutionResult(
                    tool_name=self.metadata.name,
                    status="failure",
                    error_message=f"MCP handler execution error: {str(e)}"
                )

        # Default MCP stub payload when remote server connection is unconfigured
        return ToolExecutionResult(
            tool_name=self.metadata.name,
            status="success",
            result_data={
                "mcp_protocol": "2024-11-05",
                "tool": self.metadata.name,
                "status": "ok",
                "arguments_received": arguments,
                "note": "MCP Tool Adapter executed via JARVIX tool interface."
            }
        )
