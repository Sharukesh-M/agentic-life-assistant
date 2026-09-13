"""
Controlled Mock Tools for Testing & Local Execution without external credentials.
"""

from app.tools.mocks.calendar import MockCalendarCreateEventTool, MockCalendarListEventsTool
from app.tools.mocks.github import MockGitHubGetRecentActivityTool
from app.tools.mocks.notifications import MockNotificationSendTool

def register_mock_tools(registry=None):
    """Utility function to register all mock tools into given or default ToolRegistry."""
    from app.tools.registry import ToolRegistry
    if registry is None:
        registry = ToolRegistry.get_instance()

    registry.register(MockCalendarCreateEventTool())
    registry.register(MockCalendarListEventsTool())
    registry.register(MockGitHubGetRecentActivityTool())
    registry.register(MockNotificationSendTool())
    return registry
