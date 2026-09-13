"""
Application-Level Tool Authorization Engine.
Enforces permissions and token validation before tool execution.
"""

from typing import Tuple, Optional
from app.tools.base import BaseTool
from app.tools.context import ToolExecutionContext

class ToolAuthorizationEngine:
    """
    Enforces application-level access control policies.
    """

    @staticmethod
    def is_authorized(
        tool: BaseTool,
        context: Optional[ToolExecutionContext] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates authorization policy for requested tool and context.
        Checked BEFORE tool execution.
        """
        metadata = tool.metadata

        # 1. If tool does not require authorization, allow by default
        if not metadata.requires_authorization:
            return True, "Tool does not require authorization."

        # 2. If tool requires authorization, context must be provided
        if context is None:
            return False, f"Authorization context missing for protected tool '{metadata.name}'."

        # 3. Check specific required permission if defined
        if metadata.required_permission:
            if not context.is_permission_granted(metadata.required_permission):
                return False, f"Permission '{metadata.required_permission}' not granted to user '{context.user_id}'."

        # 4. Check authorization token for external APIs / OAuth tools
        if metadata.external_side_effect or metadata.requires_authorization:
            token = context.authorization_tokens.get(metadata.name) or context.authorization_tokens.get("global")
            if not token and not context.is_permission_granted("admin"):
                return False, f"Valid authorization token required for tool '{metadata.name}'."

        return True, "Authorization granted."
