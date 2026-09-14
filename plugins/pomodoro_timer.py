"""
pomodoro_timer.py — focus/study timer for JARVIS
Drop into plugins/. No config needed — pure in-memory timer.

Runs a work session, then automatically starts a break and speaks when
each phase ends (via player.write_log, same as the rest of the app).
Good fit for study sessions: "start a 25 minute focus timer".
"""

import time
import threading

PLUGIN = {
    "name": "pomodoro_timer",
    "description": (
        "Run a focus/study timer with automatic work and break cycles "
        "(Pomodoro technique). Trigger phrases: 'start a focus timer', "
        "'start a 25 minute study session', 'how much time is left', "
        "'stop the timer'. Do NOT use reminder.py for this — that tool "
        "fires a single one-off OS notification, this one runs a repeating "
        "work/break cycle and speaks when each phase ends."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["start", "status", "stop"],
                "description": "start a new session, check time remaining, or stop the timer.",
            },
            "work_minutes": {"type": "INTEGER", "description": "Length of the focus phase, default 25."},
            "break_minutes": {"type": "INTEGER", "description": "Length of the break phase, default 5."},
        },
        "required": ["action"],
    },
}

_state = {"end_time": None, "phase": None, "timer": None}


def _speak_later(player, message):
    if player:
        try:
            player.write_log(f"JARVIS: {message}")
        except Exception:
            pass


def _start(work_minutes, break_minutes, player):
    work = work_minutes or 25
    brk = break_minutes or 5

    def _on_break_done():
        _speak_later(player, "Break's over — ready for another focus session?")
        _state.update({"end_time": None, "phase": None, "timer": None})

    def _on_work_done():
        _state["phase"] = "break"
        _state["end_time"] = time.time() + brk * 60
        _speak_later(player, f"Focus session done — time for a {brk} minute break.")
        t = threading.Timer(brk * 60, _on_break_done)
        t.daemon = True
        t.start()
        _state["timer"] = t

    _state["phase"] = "work"
    _state["end_time"] = time.time() + work * 60
    t = threading.Timer(work * 60, _on_work_done)
    t.daemon = True
    t.start()
    _state["timer"] = t

    return f"Started a {work} minute focus session, sir. I'll let you know when it's break time."


def _status():
    if not _state["end_time"]:
        return "No timer is currently running."
    remaining = max(0, int(_state["end_time"] - time.time()))
    mins, secs = divmod(remaining, 60)
    return f"{_state['phase'].capitalize()} phase — {mins}m {secs}s remaining."


def _stop():
    if _state["timer"]:
        _state["timer"].cancel()
    was_running = _state["end_time"] is not None
    _state.update({"end_time": None, "phase": None, "timer": None})
    return "Timer stopped." if was_running else "No timer was running."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    try:
        if action == "start":
            result_text = _start(parameters.get("work_minutes"), parameters.get("break_minutes"), player)
        elif action == "status":
            result_text = _status()
        elif action == "stop":
            result_text = _stop()
        else:
            result_text = f"Sir, I don't recognize the timer action '{action}'."
    except Exception as e:
        return f"Sir, pomodoro_timer failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text