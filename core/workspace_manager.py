"""
core/workspace_manager.py — Central Application State & Workspace Manager for JARVIS-X

Manages active workspace navigation, central application state, UI event dispatching,
and structured execution pipeline logging.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Dict

logger = logging.getLogger("jarvis.workspace")


# ── Structured Logging Helper ────────────────────────────────────────────────

def debug_log(tag: str, message: str):
    """Print uniform structured debug log for execution pipeline tracing."""
    formatted = f"[{tag.upper()}] {message}"
    print(formatted)
    logger.info(formatted)


# ── Workspace Types ──────────────────────────────────────────────────────────

class WorkspaceName(str, Enum):
    HOME      = "HOME"
    TASKS     = "TASKS"
    GOALS     = "GOALS"
    LEARNING  = "LEARNING"
    PROGRESS  = "PROGRESS"
    DEVICES   = "DEVICES"
    CALLS     = "CALLS"
    MEMORY    = "MEMORY"
    SETTINGS  = "SETTINGS"
    PROFILE   = "PROFILE"


# ── Central Workspace & Selection State ──────────────────────────────────────

@dataclass
class WorkspaceState:
    active_workspace: WorkspaceName = WorkspaceName.HOME
    selected_task_id: Optional[str] = None
    selected_goal_id: Optional[str] = None
    selected_learning_content_id: Optional[str] = None
    last_error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_workspace": self.active_workspace.value,
            "selected_task_id": self.selected_task_id,
            "selected_goal_id": self.selected_goal_id,
            "selected_learning_content_id": self.selected_learning_content_id,
            "last_error": self.last_error,
        }


# ── Event System & Listeners ─────────────────────────────────────────────────

class EventType(str, Enum):
    TASK_CREATED            = "TASK_CREATED"
    TASK_UPDATED            = "TASK_UPDATED"
    TASK_COMPLETED          = "TASK_COMPLETED"
    TASK_POSTPONED          = "TASK_POSTPONED"
    TASK_RESCHEDULED        = "TASK_RESCHEDULED"
    TASK_DELETED            = "TASK_DELETED"
    WORKSPACE_OPENED        = "WORKSPACE_OPENED"
    LEARNING_SESSION_STARTED = "LEARNING_SESSION_STARTED"
    LEARNING_PROGRESS_UPDATED= "LEARNING_PROGRESS_UPDATED"


_EVENT_LISTENERS: list[Callable[[str, dict], None]] = []
_LISTENERS_LOCK = threading.Lock()


def register_event_listener(listener: Callable[[str, dict], None]):
    """Register callback for system & UI state events."""
    with _LISTENERS_LOCK:
        if listener not in _EVENT_LISTENERS:
            _EVENT_LISTENERS.append(listener)


def emit_event(event_type: str | EventType, payload: dict | None = None):
    """Emit a system event to all registered UI & state listeners."""
    evt_name = event_type.value if isinstance(event_type, EventType) else str(event_type)
    payload_dict = payload or {}
    debug_log("EVENT", f"Emitted {evt_name} with payload keys: {list(payload_dict.keys())}")
    
    with _LISTENERS_LOCK:
        listeners = list(_EVENT_LISTENERS)

    for listener in listeners:
        try:
            listener(evt_name, payload_dict)
        except Exception as exc:
            debug_log("EVENT_ERROR", f"Error in event listener for {evt_name}: {exc}")


# ── Workspace Manager Singleton ──────────────────────────────────────────────

class WorkspaceManager:
    _instance: Optional["WorkspaceManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.state = WorkspaceState()
        self._ui_callback: Optional[Callable[[str, dict], None]] = None

    @classmethod
    def get(cls) -> "WorkspaceManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_ui_callback(self, callback: Callable[[str, dict], None]):
        self._ui_callback = callback
        register_event_listener(callback)

    def set_active_workspace(self, workspace: WorkspaceName | str) -> bool:
        if isinstance(workspace, str):
            try:
                workspace = WorkspaceName(workspace.upper())
            except ValueError:
                debug_log("WORKSPACE", f"Unknown workspace name '{workspace}'")
                self.state.last_error = f"Invalid workspace name: {workspace}"
                return False

        old_ws = self.state.active_workspace
        self.state.active_workspace = workspace
        self.state.last_error = None
        debug_log("WORKSPACE", f"State transition: {old_ws.value} -> {workspace.value}")

        emit_event(EventType.WORKSPACE_OPENED, {
            "workspace": workspace.value,
            "state": self.state.to_dict(),
        })

        if self._ui_callback:
            try:
                self._ui_callback("open_workspace", {"workspace": workspace.value})
            except Exception as e:
                debug_log("UI_STATE", f"Error in UI workspace callback: {e}")

        return True

    def open_workspace(self, name: str) -> dict[str, Any]:
        """Generic open_workspace tool execution."""
        debug_log("TOOL_CALL", f"open_workspace(name='{name}')")
        ok = self.set_active_workspace(name)
        if ok:
            debug_log("TOOL_RESULT", f"success=True workspace={self.state.active_workspace.value}")
            return {
                "success": True,
                "workspace": self.state.active_workspace.value,
                "state": self.state.to_dict(),
            }
        else:
            debug_log("TOOL_RESULT", f"success=False error={self.state.last_error}")
            return {
                "success": False,
                "error": self.state.last_error or f"Failed to open workspace '{name}'",
            }

    # ── Specialized Workspace Wrappers ───────────────────────────────────────

    def open_home(self) -> dict[str, Any]:
        return self.open_workspace("HOME")

    def open_task_workspace(self) -> dict[str, Any]:
        return self.open_workspace("TASKS")

    def open_goals_workspace(self) -> dict[str, Any]:
        return self.open_workspace("GOALS")

    def open_learning_workspace(self) -> dict[str, Any]:
        return self.open_workspace("LEARNING")

    def open_progress_workspace(self) -> dict[str, Any]:
        return self.open_workspace("PROGRESS")

    def open_devices_workspace(self) -> dict[str, Any]:
        return self.open_workspace("DEVICES")

    def open_calls_workspace(self) -> dict[str, Any]:
        return self.open_workspace("CALLS")

    def open_memory_workspace(self) -> dict[str, Any]:
        return self.open_workspace("MEMORY")

    def open_settings_workspace(self) -> dict[str, Any]:
        return self.open_workspace("SETTINGS")

    def open_profile_workspace(self) -> dict[str, Any]:
        return self.open_workspace("PROFILE")


def get_workspace_manager() -> WorkspaceManager:
    return WorkspaceManager.get()
