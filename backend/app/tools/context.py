"""
Tool Execution Context Container.
Provides user identity, authorization tokens, confirmation state, and DB session reference.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class ToolExecutionContext:
    user_id: str = "default_user"
    user_permissions: List[str] = field(default_factory=list)
    authorization_tokens: Dict[str, str] = field(default_factory=dict)
    confirmed_by_user: bool = False
    db_session: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_permission_granted(self, required_permission: str) -> bool:
        """Checks if user context contains required permission or wildcard admin."""
        if "*" in self.user_permissions or "admin" in self.user_permissions:
            return True
        return required_permission in self.user_permissions
