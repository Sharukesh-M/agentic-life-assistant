"""
habit_tracker.py — daily habit streaks for JARVIS
Drop into plugins/. Stores habits in memory/habits.json.

Good for "did I study today"-style accountability: log a habit once a
day, ask for the current streak, and it tells you whether you've kept
it going or broken the chain.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

DATA_PATH = Path(__file__).resolve().parent.parent / "memory" / "habits.json"

PLUGIN = {
    "name": "habit_tracker",
    "description": (
        "Track daily habits and streaks, like 'studied today' or "
        "'exercised today'. Trigger phrases: 'log that I studied today', "
        "'mark ... as done for today', 'what's my streak for...', "
        "'show my habits'. Use goal_tracker for longer-term progress "
        "narratives, and this tool specifically for simple daily "
        "yes/no habit logging and streak counts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["log", "streak", "list"],
                "description": "mark a habit done for today, check a habit's current streak, or list all tracked habits.",
            },
            "habit": {"type": "STRING", "description": "Habit name, e.g. 'GATE study' (required for 'log' and 'streak')."},
        },
        "required": ["action"],
    },
}


def _load():
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _save(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _log(habit):
    data = _load()
    today = datetime.now().date().isoformat()
    dates = data.setdefault(habit, [])
    if today in dates:
        return f"Already logged '{habit}' for today."
    dates.append(today)
    _save(data)
    streak = _compute_streak(dates)
    return f"Logged '{habit}' for today. Current streak: {streak} day(s)."


def _compute_streak(dates):
    date_set = set(dates)
    today = datetime.now().date()
    streak = 0
    cursor = today
    # Today may not be logged yet — start counting from today if present, else yesterday
    if today.isoformat() not in date_set:
        cursor = today - timedelta(days=1)
    while cursor.isoformat() in date_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _streak(habit):
    data = _load()
    dates = data.get(habit)
    if not dates:
        return f"No history for '{habit}' yet — log it once to start a streak."
    streak = _compute_streak(dates)
    today = datetime.now().date().isoformat()
    if streak == 0:
        return f"'{habit}' streak is broken — log it today to start a new one."
    logged_today = " (logged today)" if today in dates else " (not logged today yet)"
    return f"'{habit}' streak: {streak} day(s){logged_today}."


def _list():
    data = _load()
    if not data:
        return "You're not tracking any habits yet."
    lines = [f"{habit}: {_compute_streak(dates)} day streak" for habit, dates in data.items()]
    return "Habits: " + "; ".join(lines)


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    habit = parameters.get("habit")

    try:
        if action == "log":
            result_text = "Which habit should I log?" if not habit else _log(habit)
        elif action == "streak":
            result_text = "Which habit's streak do you want?" if not habit else _streak(habit)
        elif action == "list":
            result_text = _list()
        else:
            result_text = f"Sir, I don't recognize the habit action '{action}'."
    except Exception as e:
        return f"Sir, habit_tracker plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text