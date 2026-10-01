"""
core/voice_controller.py - JARVIS-X Voice Controller

Phase 2 addition: Explicit voice state machine and barge-in enhancement.

This wraps and extends the existing JarvisLive voice logic without replacing
it. In Phase 2, VoiceController is a standalone class that:

  1. Owns the VoiceStateEnum state machine (validated transitions)
  2. Provides a clean barge-in detection hook
  3. Exposes callbacks that JarvisLive can bind to

Migration strategy:
  Phase 2 -- VoiceController exists independently; JarvisLive unchanged
  Phase 5 -- JarvisLive delegates set_speaking(), interrupt() to VoiceController

No existing code is modified.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from core.state_manager import SessionState, VoiceStateEnum

logger = logging.getLogger("jarvis.voice_controller")


# ---------------------------------------------------------------------------
# Barge-in detection config
# ---------------------------------------------------------------------------

BARGE_IN_RMS_THRESHOLD = 200.0   # RMS above which mic audio counts as speech
BARGE_IN_HOLD_MS       = 200     # ms of continuous speech to confirm barge-in
BARGE_IN_COOLDOWN_S    = 1.5     # seconds after barge-in before it can fire again


# ---------------------------------------------------------------------------
# VoiceController
# ---------------------------------------------------------------------------

class VoiceController:
    """Manages the JARVIS-X voice lifecycle state machine.

    Callbacks (all optional, set after construction):
        on_state_change(new_state: VoiceStateEnum) -> None
            Called after every successful state transition.
        on_barge_in() -> None
            Called when the barge-in detector fires while JARVIS is speaking.
        on_turn_complete() -> None
            Called when the LLM signals turn_complete and the state transitions
            to TURN_COMPLETE.
    """

    def __init__(self, session: Optional[SessionState] = None) -> None:
        # Use a provided session (shared with AppState) or create a private one
        self._session = session or SessionState()
        self._lock = threading.Lock()

        # Barge-in detector state
        self._barge_speech_start: float = 0.0
        self._last_barge_in: float = 0.0
        self._barge_in_armed = False

        # Callbacks
        self.on_state_change: Optional[Callable[[VoiceStateEnum], None]] = None
        self.on_barge_in: Optional[Callable[[], None]] = None
        self.on_turn_complete: Optional[Callable[[], None]] = None

        self._log = lambda m: logger.info(m)

    # ── State transitions ────────────────────────────────────────────────────

    def transition(self, new_state: VoiceStateEnum) -> bool:
        """Attempt a validated state transition. Returns True if applied."""
        ok = self._session.transition_voice(new_state)
        if ok and self.on_state_change:
            try:
                self.on_state_change(new_state)
            except Exception as exc:
                self._log(f"[VoiceController] on_state_change callback error: {exc}")
        return ok

    def force(self, new_state: VoiceStateEnum) -> None:
        """Unconditional state override (error recovery / tests)."""
        self._session.force_voice(new_state)
        if self.on_state_change:
            try:
                self.on_state_change(new_state)
            except Exception:
                pass

    @property
    def state(self) -> VoiceStateEnum:
        return self._session.voice

    # ── Lifecycle helpers  (mirror JarvisLive's public interface) ────────────

    def start_speaking(self) -> None:
        """Call when JARVIS starts playing audio to the speaker."""
        self.transition(VoiceStateEnum.SPEAKING)
        self._barge_in_armed = True   # enable barge-in during speech

    def stop_speaking(self) -> None:
        """Call when JARVIS finishes playing audio (turn complete + queue empty)."""
        self._barge_in_armed = False
        self.transition(VoiceStateEnum.LISTENING)

    def start_listening(self) -> None:
        """Call when mic is opened and JARVIS is waiting for user speech."""
        self.transition(VoiceStateEnum.LISTENING)

    def mark_user_speaking(self) -> None:
        """Call when VAD detects user speech has started."""
        self.transition(VoiceStateEnum.USER_SPEAKING)

    def mark_user_paused(self) -> None:
        """Call when a brief silence is detected mid-utterance."""
        self.transition(VoiceStateEnum.USER_PAUSED)

    def mark_turn_complete(self) -> None:
        """Call when the LLM signals turn_complete."""
        ok = self.transition(VoiceStateEnum.TURN_COMPLETE)
        if ok and self.on_turn_complete:
            try:
                self.on_turn_complete()
            except Exception:
                pass

    def mark_thinking(self) -> None:
        """Call when a tool call has been dispatched and JARVIS is processing."""
        self.transition(VoiceStateEnum.THINKING)

    def mark_responding(self) -> None:
        """Call when the LLM response is ready and audio is about to play."""
        self.transition(VoiceStateEnum.RESPONDING)

    def interrupt(self) -> None:
        """Barge-in: user started speaking while JARVIS was talking.

        Sets state to INTERRUPTED then immediately to LISTENING.
        The caller is responsible for draining audio_in_queue.
        """
        self._barge_in_armed = False
        self._last_barge_in = time.monotonic()
        self.force(VoiceStateEnum.INTERRUPTED)
        self.transition(VoiceStateEnum.LISTENING)
        self._log("[VoiceController] Barge-in: interrupted -> listening")
        if self.on_barge_in:
            try:
                self.on_barge_in()
            except Exception:
                pass

    def sleep(self) -> None:
        """Put JARVIS to sleep (wake-word mode)."""
        self._barge_in_armed = False
        self.force(VoiceStateEnum.SLEEPING)
        self._session.awake = False

    def wake(self) -> None:
        """Wake JARVIS from sleep."""
        self._session.awake = True
        self._session.last_user_speech = time.monotonic()
        self.force(VoiceStateEnum.LISTENING)

    # ── Barge-in detection ───────────────────────────────────────────────────

    def feed_mic_level(self, rms: float) -> None:
        """Feed real-time RMS level from the microphone callback.

        Called from the sounddevice audio callback thread (must be fast).
        Detects sustained speech while JARVIS is speaking and fires barge-in.

        Integration in main.py (Phase 5):
            In the mic callback, after computing _pcm_level(), call:
                voice_controller.feed_mic_level(rms_value)
        """
        if not self._barge_in_armed:
            return

        # Cooldown: don't fire again too soon after a barge-in
        if (time.monotonic() - self._last_barge_in) < BARGE_IN_COOLDOWN_S:
            return

        if rms >= BARGE_IN_RMS_THRESHOLD:
            if self._barge_speech_start == 0.0:
                self._barge_speech_start = time.monotonic()
            elif (time.monotonic() - self._barge_speech_start) * 1000 >= BARGE_IN_HOLD_MS:
                # Sustained speech confirmed -- fire barge-in
                self._barge_speech_start = 0.0
                self.interrupt()
        else:
            # Reset the hold counter if speech dropped below threshold
            self._barge_speech_start = 0.0

    # ── Predicates ──────────────────────────────────────────────────────────

    def is_speaking(self) -> bool:
        return self._session.is_speaking()

    def is_listening(self) -> bool:
        return self._session.is_listening()

    def is_busy(self) -> bool:
        return self._session.is_busy()

    def is_asleep(self) -> bool:
        return self._session.is_asleep()

    # ── Observability ────────────────────────────────────────────────────────

    def describe(self) -> dict:
        return {
            "state":          self.state.value,
            "awake":          self._session.awake,
            "barge_in_armed": self._barge_in_armed,
        }
