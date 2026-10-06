"""
core/state_manager.py - JARVIS-X Centralized State Models

Phase 2 addition: Provides typed, centralized state dataclasses that will
gradually replace the scattered flags in JarvisLive (_is_speaking, _awake,
_interrupted, _vision_busy, etc.).

No existing code is modified by this module. JarvisLive continues to work
as before; these models are made available for new modules to import.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Voice States
# ---------------------------------------------------------------------------

class VoiceStateEnum(str, Enum):
    """Explicit voice lifecycle states for JARVIS-X.

    Legal transitions:
        IDLE          -> LISTENING | SLEEPING
        LISTENING     -> USER_SPEAKING | SLEEPING | THINKING | IDLE
        USER_SPEAKING -> USER_PAUSED | TURN_COMPLETE | INTERRUPTED
        USER_PAUSED   -> USER_SPEAKING | TURN_COMPLETE
        TURN_COMPLETE -> THINKING
        THINKING      -> RESPONDING | LISTENING
        RESPONDING    -> SPEAKING | LISTENING
        SPEAKING      -> LISTENING | INTERRUPTED
        INTERRUPTED   -> LISTENING
        SLEEPING      -> LISTENING | IDLE
        any           -> IDLE  (emergency escape hatch)
    """
    IDLE          = "idle"
    LISTENING     = "listening"
    USER_SPEAKING = "user_speaking"
    USER_PAUSED   = "user_paused"
    TURN_COMPLETE = "turn_complete"
    THINKING      = "thinking"
    RESPONDING    = "responding"
    SPEAKING      = "speaking"
    INTERRUPTED   = "interrupted"
    SLEEPING      = "sleeping"


_LEGAL_TRANSITIONS: dict[VoiceStateEnum, set[VoiceStateEnum]] = {
    VoiceStateEnum.IDLE: {
        VoiceStateEnum.LISTENING,
        VoiceStateEnum.SLEEPING,
    },
    VoiceStateEnum.LISTENING: {
        VoiceStateEnum.LISTENING,
        VoiceStateEnum.USER_SPEAKING,
        VoiceStateEnum.SLEEPING,
        VoiceStateEnum.THINKING,
        VoiceStateEnum.IDLE,
    },
    VoiceStateEnum.USER_SPEAKING: {
        VoiceStateEnum.USER_PAUSED,
        VoiceStateEnum.TURN_COMPLETE,
        VoiceStateEnum.INTERRUPTED,
    },
    VoiceStateEnum.USER_PAUSED: {
        VoiceStateEnum.USER_SPEAKING,
        VoiceStateEnum.TURN_COMPLETE,
    },
    VoiceStateEnum.TURN_COMPLETE: {
        VoiceStateEnum.THINKING,
    },
    VoiceStateEnum.THINKING: {
        VoiceStateEnum.RESPONDING,
        VoiceStateEnum.LISTENING,
    },
    VoiceStateEnum.RESPONDING: {
        VoiceStateEnum.SPEAKING,
        VoiceStateEnum.LISTENING,
    },
    VoiceStateEnum.SPEAKING: {
        VoiceStateEnum.LISTENING,
        VoiceStateEnum.INTERRUPTED,
    },
    VoiceStateEnum.INTERRUPTED: {
        VoiceStateEnum.LISTENING,
    },
    VoiceStateEnum.SLEEPING: {
        VoiceStateEnum.LISTENING,
        VoiceStateEnum.IDLE,
    },
}


# ---------------------------------------------------------------------------
# Sub-state dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VisionState:
    """Tracks the state of the vision capture pipeline."""
    busy: bool = False
    cam_active: bool = False
    close_pending: bool = False
    last_capture_time: float = 0.0
    pending_bytes: Optional[bytes] = None
    pending_mime: Optional[str] = None
    pending_question: Optional[str] = None
    pending_angle: Optional[str] = None

    def reset(self) -> None:
        """Clear all pending vision state."""
        self.busy = False
        self.cam_active = False
        self.close_pending = False
        self.pending_bytes = None
        self.pending_mime = None
        self.pending_question = None
        self.pending_angle = None


@dataclass
class ConnectionState:
    """Tracks Gemini Live connection state."""
    connected: bool = False
    resume_handle: Optional[str] = None
    enhanced_live: bool = True   # proactive audio; disabled if API rejects it
    conn_backoff: int = 3


# ---------------------------------------------------------------------------
# Session State
# ---------------------------------------------------------------------------

@dataclass
class SessionState:
    """Complete runtime state for one JarvisLive session.

    This is the target replacement for the scattered instance variables in
    JarvisLive. During the transition, both coexist: JarvisLive reads from
    its own attributes; new modules (agents, orchestrator) read from SessionState.
    """
    voice: VoiceStateEnum = VoiceStateEnum.IDLE
    vision: VisionState = field(default_factory=VisionState)
    connection: ConnectionState = field(default_factory=ConnectionState)

    # Wake-word gating
    wake_enabled: bool = False
    awake: bool = True

    # Phone mic bridge (remote dashboard)
    phone_active: bool = False

    # Timestamps (monotonic)
    last_user_speech: float = field(default_factory=time.monotonic)
    session_start: float = field(default_factory=time.monotonic)

    # Conversation log for session summary
    session_log: list = field(default_factory=list)

    # Identity (read from config at startup)
    assistant_name: str = "JARVIS"
    user_name: str = ""

    # One-shot flags
    briefing_sent: bool = False

    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False, hash=False
    )

    def transition_voice(self, new_state: VoiceStateEnum) -> bool:
        """Attempt a voice state transition.

        Returns True if legal and applied.
        Returns False and logs a warning if illegal.
        Never raises -- a bad caller must never kill the audio pipeline.
        """
        with self._lock:
            allowed = _LEGAL_TRANSITIONS.get(self.voice, set())
            if new_state == VoiceStateEnum.IDLE or new_state in allowed:
                old = self.voice
                self.voice = new_state
                print(f"[State] voice {old.value} -> {new_state.value}")
                return True
            print(
                f"[State] WARNING: illegal transition {self.voice.value} -> "
                f"{new_state.value} (allowed: {sorted(s.value for s in allowed)})"
            )
            return False

    def force_voice(self, new_state: VoiceStateEnum) -> None:
        """Unconditional voice state override (for error recovery / tests)."""
        with self._lock:
            old = self.voice
            self.voice = new_state
            print(f"[State] FORCE {old.value} -> {new_state.value}")

    def is_speaking(self) -> bool:
        return self.voice == VoiceStateEnum.SPEAKING

    def is_listening(self) -> bool:
        return self.voice in (
            VoiceStateEnum.LISTENING,
            VoiceStateEnum.USER_SPEAKING,
            VoiceStateEnum.USER_PAUSED,
        )

    def is_busy(self) -> bool:
        """True when JARVIS should not receive proactive messages."""
        return self.voice in (
            VoiceStateEnum.SPEAKING,
            VoiceStateEnum.THINKING,
            VoiceStateEnum.RESPONDING,
        )

    def is_asleep(self) -> bool:
        return self.voice == VoiceStateEnum.SLEEPING or not self.awake


# ---------------------------------------------------------------------------
# Application State  (process-lifetime singleton)
# ---------------------------------------------------------------------------

class AppState:
    """Process-lifetime application state container.

    Provides a single shared instance accessible from any module without
    circular imports. Created lazily on first access.

    Usage:
        from core.state_manager import AppState, VoiceStateEnum
        state = AppState.get()
        state.session.transition_voice(VoiceStateEnum.LISTENING)
    """

    _instance: Optional["AppState"] = None
    _cls_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.session = SessionState()
        # Open-ended extension bag so modules can attach state
        # without modifying this class (e.g. AgentRegistry attaches itself)
        self.extra: dict[str, Any] = {}

    @classmethod
    def get(cls) -> "AppState":
        """Return the process singleton, creating it on first call."""
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (for test isolation only)."""
        with cls._cls_lock:
            cls._instance = None

    def __repr__(self) -> str:
        s = self.session
        return (
            f"AppState(voice={s.voice.value}, "
            f"awake={s.awake}, "
            f"assistant={s.assistant_name})"
        )


def get_app_state() -> AppState:
    """Return the process-level AppState singleton."""
    return AppState.get()

