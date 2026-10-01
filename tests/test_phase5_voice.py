"""
tests/test_phase5_voice.py - JARVIS-X Phase 5 Voice State Machine & Barge-in Tests

Tests state transitions, barge-in detection, callback triggers, and integration with
JarvisLive.
"""

import time
import pytest
from unittest.mock import MagicMock

from core.voice_controller import VoiceController, BARGE_IN_RMS_THRESHOLD
from core.state_manager import SessionState, VoiceStateEnum, get_app_state


def test_voice_controller_initial_state():
    session = SessionState()
    vc = VoiceController(session=session)
    assert vc.state == VoiceStateEnum.IDLE
    assert not vc.is_speaking()
    assert vc.describe()["state"] == "idle"


def test_voice_controller_happy_path_transitions():
    vc = VoiceController()
    states_logged = []
    vc.on_state_change = lambda s: states_logged.append(s)

    vc.start_listening()
    assert vc.state == VoiceStateEnum.LISTENING

    vc.mark_user_speaking()
    assert vc.state == VoiceStateEnum.USER_SPEAKING

    vc.mark_turn_complete()
    assert vc.state == VoiceStateEnum.TURN_COMPLETE

    vc.mark_thinking()
    assert vc.state == VoiceStateEnum.THINKING

    vc.mark_responding()
    assert vc.state == VoiceStateEnum.RESPONDING

    vc.start_speaking()
    assert vc.state == VoiceStateEnum.SPEAKING
    assert vc.is_speaking()

    vc.stop_speaking()
    assert vc.state == VoiceStateEnum.LISTENING

    assert len(states_logged) == 7


def test_barge_in_detection_triggers_interrupt():
    vc = VoiceController()
    barge_in_fired = False

    def _on_barge_in():
        nonlocal barge_in_fired
        barge_in_fired = True

    vc.on_barge_in = _on_barge_in
    vc.start_listening()
    vc.mark_user_speaking()
    vc.mark_turn_complete()
    vc.mark_thinking()
    vc.mark_responding()
    vc.start_speaking()
    assert vc.is_speaking()

    # Feed low RMS (silence) -> no barge in
    vc.feed_mic_level(50.0)
    assert not barge_in_fired

    # Feed high RMS continuously for >200ms -> should trigger barge in
    vc.feed_mic_level(BARGE_IN_RMS_THRESHOLD + 100.0)
    time.sleep(0.25)
    vc.feed_mic_level(BARGE_IN_RMS_THRESHOLD + 100.0)

    assert barge_in_fired
    assert vc.state == VoiceStateEnum.LISTENING  # interrupt transitions to listening
    assert not vc.is_speaking()


def test_sleep_and_wake_transitions():
    vc = VoiceController()
    vc.start_listening()
    assert vc.state == VoiceStateEnum.LISTENING

    vc.sleep()
    assert vc.state == VoiceStateEnum.SLEEPING
    assert vc.is_asleep()

    vc.wake()
    assert vc.state == VoiceStateEnum.LISTENING
    assert not vc.is_asleep()


def test_main_py_imports_and_voice_controller_wiring():
    """Verify main.py can be imported cleanly and VoiceController is integrated."""
    import main
    assert hasattr(main, "VoiceController")
    assert hasattr(main, "VoiceStateEnum")
    assert hasattr(main.JarvisLive, "set_speaking")
    assert hasattr(main.JarvisLive, "interrupt")
