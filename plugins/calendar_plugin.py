"""
calendar_plugin.py — lightweight local calendar for JARVIS
Drop into plugins/. Stores events in memory/calendar.json (created on first use).

This is local-only by design (no OAuth setup needed). To sync with real
Google Calendar instead, swap _load/_save for calls to the Google Calendar
API (google-api-python-client) and keep the same PLUGIN interface.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_PATH = Path(__file__).resolve().parent.parent / "memory" / "calendar.json"

PLUGIN = {
    "name": "calendar",
    "description": (
        "Add, list, or remove calendar events/reminders. Trigger phrases: "
        "'add an event...', 'put ... on my calendar', 'what's on my "
        "calendar today', 'what do I have coming up', 'remove/delete event...'. "
        "Do NOT use reminder.py for this — that tool fires OS notifications "
        "at a specific time, this one is a browsable event list."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["add", "list", "remove", "today"],
                "description": "add a new event, list upcoming events, remove one, or list today's events.",
            },
            "title": {"type": "STRING", "description": "Event title (required for 'add')."},
            "when": {
                "type": "STRING",
                "description": "Date and time as 'YYYY-MM-DD HH:MM' (required for 'add').",
            },
            "event_id": {"type": "STRING", "description": "Event ID to remove (required for 'remove')."},
        },
        "required": ["action"],
    },
}


def _load():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _save(events):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(events, indent=2), encoding="utf-8")


def _add(title, when_str):
    try:
        dt = datetime.strptime(when_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return "Please give the date and time like '2026-10-05 14:30'."

    events = _load()
    event = {"id": uuid.uuid4().hex[:8], "title": title, "datetime": dt.isoformat()}
    events.append(event)
    events.sort(key=lambda e: e["datetime"])
    _save(events)
    return f"Added '{title}' on {dt.strftime('%A, %d %B at %H:%M')}. ID: {event['id']}."


def _list():
    events = _load()
    now = datetime.now()
    upcoming = [e for e in events if datetime.fromisoformat(e["datetime"]) >= now]
    if not upcoming:
        return "You have no upcoming events."
    lines = [
        f"{e['title']} — {datetime.fromisoformat(e['datetime']).strftime('%a %d %b, %H:%M')} (id: {e['id']})"
        for e in upcoming[:10]
    ]
    return "Upcoming events: " + "; ".join(lines)


def _today():
    events = _load()
    today = datetime.now().date()
    todays = [e for e in events if datetime.fromisoformat(e["datetime"]).date() == today]
    if not todays:
        return "Nothing on your calendar today."
    lines = [f"{e['title']} at {datetime.fromisoformat(e['datetime']).strftime('%H:%M')}" for e in todays]
    return "Today: " + "; ".join(lines)


def _remove(event_id):
    events = _load()
    remaining = [e for e in events if e["id"] != event_id]
    if len(remaining) == len(events):
        return f"No event found with id {event_id}."
    _save(remaining)
    return f"Removed event {event_id}."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    title = parameters.get("title")
    when = parameters.get("when")
    event_id = parameters.get("event_id")

    try:
        if action == "add":
            result_text = (
                "I need a title and a date/time to add an event."
                if not (title and when)
                else _add(title, when)
            )
        elif action == "list":
            result_text = _list()
        elif action == "today":
            result_text = _today()
        elif action == "remove":
            result_text = "Which event id should I remove?" if not event_id else _remove(event_id)
        else:
            result_text = f"Sir, I don't recognize the calendar action '{action}'."
    except Exception as e:
        return f"Sir, calendar plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text