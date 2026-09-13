"""
Tool Exception Hierarchy for JARVIX Execution Discipline.
"""

class ToolError(Exception):
    """Base exception for all tool-related errors."""
    pass

class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered in the ToolRegistry."""
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' is not available in the tool registry.")
        self.tool_name = tool_name

class ToolAuthorizationError(ToolError):
    """Raised when a tool execution request fails the application-level authorization check."""
    def __init__(self, tool_name: str, reason: str):
        super().__init__(f"Authorization denied for tool '{tool_name}': {reason}")
        self.tool_name = tool_name
        self.reason = reason

class ToolConfirmationRequiredError(ToolError):
    """Raised when a high-impact tool requires explicit user confirmation before execution."""
    def __init__(self, tool_name: str, confirmation_prompt: str):
        super().__init__(f"Tool '{tool_name}' requires confirmation: {confirmation_prompt}")
        self.tool_name = tool_name
        self.confirmation_prompt = confirmation_prompt

class ToolValidationError(ToolError):
    """Raised when tool input arguments fail schema validation."""
    def __init__(self, tool_name: str, errors: str):
        super().__init__(f"Input validation failed for tool '{tool_name}': {errors}")
        self.tool_name = tool_name
        self.errors = errors

class ToolExecutionError(ToolError):
    """Raised when a tool encounters a runtime failure during execution."""
    def __init__(self, tool_name: str, message: str):
        super().__init__(f"Runtime failure during execution of tool '{tool_name}': {message}")
        self.tool_name = tool_name
        self.message = message

class ToolVerificationError(ToolError):
    """Raised when a tool result fails verification (e.g. false success claim)."""
    def __init__(self, tool_name: str, reason: str):
        super().__init__(f"Result verification failed for tool '{tool_name}': {reason}")
        self.tool_name = tool_name
        self.reason = reason
