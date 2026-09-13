"""
Central Tool Registry for JARVIX Capabilities.
Single Source of Truth for runtime tool discovery and metadata catalog.
"""

import threading
from typing import Dict, List, Optional
from app.tools.base import BaseTool, ToolMetadata
from app.tools.errors import ToolNotFoundError

class ToolRegistry:
    """
    Central Thread-Safe Tool Registry.
    """
    _instance: Optional['ToolRegistry'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        """Returns singleton instance of ToolRegistry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance in the central catalog."""
        name = tool.metadata.name
        with self._lock:
            self._tools[name] = tool

    def unregister(self, name: str) -> bool:
        """Unregisters a tool by name."""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                return True
            return False

    def get(self, name: str) -> BaseTool:
        """Retrieves a registered tool by name. Raises ToolNotFoundError if missing."""
        with self._lock:
            if name not in self._tools:
                raise ToolNotFoundError(name)
            return self._tools[name]

    def has(self, name: str) -> bool:
        """Checks if a tool is registered."""
        with self._lock:
            return name in self._tools

    def list_tools(self) -> List[ToolMetadata]:
        """Returns metadata for all registered tools."""
        with self._lock:
            return [tool.metadata for tool in self._tools.values()]

    def list_names(self) -> List[str]:
        """Returns list of registered tool names."""
        with self._lock:
            return list(self._tools.keys())

    def clear(self) -> None:
        """Clears all registered tools."""
        with self._lock:
            self._tools.clear()
