"""
actions/comm_actions.py — JARVIS-X Communication, Call & Messaging Actions

Provides core tool handlers for:
- Initiating outgoing phone calls
- Conveying messages via phone AI assistant
- Sending WhatsApp and SMS messages
- Answering, screening, holding, and ending calls
- Transferring calls between devices (Laptop <-> Phone)
- Viewing recent call logs & AI call summaries
- Contact resolution & ambiguity checks
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from memory.comm_store import (
    CallHandlingMode,
    CallState,
    ContactRecord,
    MessageStatus,
    get_comm_store,
)
from agents.communication_agent import CommunicationAgent

# ── Active Communication UI Signal Callback ──────────────────────────────────
_COMM_UI_CALLBACK = None

def register_comm_ui_callback(fn):
    global _COMM_UI_CALLBACK
    _COMM_UI_CALLBACK = fn

def _notify_comm_ui(view_name: str, payload: dict | None = None):
    if _COMM_UI_CALLBACK:
        try:
            _COMM_UI_CALLBACK(view_name, payload or {})
        except Exception as e:
            print(f"[CommAction] UI notify error: {e}")


TOOL = {
    "name": "comm_action",
    "description": (
        "Execute communication actions across paired devices: initiate phone calls, "
        "call and convey messages, send WhatsApp/SMS messages, answer or screen incoming calls, "
        "transfer calls, end calls, resolve contacts, and show call/message summaries."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": [
                    "call_contact",
                    "convey_message",
                    "send_message",
                    "answer_call",
                    "screen_call",
                    "transfer_call",
                    "end_call",
                    "get_recent_calls",
                    "get_recent_messages",
                    "resolve_contact",
                    "set_handling_mode",
                    "open_comm_dashboard",
                ],
                "description": "The communication action to perform.",
            },
            "name": {"type": "STRING", "description": "Contact name or phone number."},
            "recipient": {"type": "STRING", "description": "Recipient contact name or number."},
            "message": {"type": "STRING", "description": "Text message content or message to convey during call."},
            "channel": {"type": "STRING", "description": "Channel: whatsapp, sms, telegram, cellular."},
            "mode": {"type": "STRING", "description": "Call handling mode: MANUAL, SCREENING, ASSISTANT, FULL_DELEGATION."},
            "is_sensitive": {"type": "BOOLEAN", "description": "Whether message contains sensitive information."},
            "confirmed": {"type": "BOOLEAN", "description": "User explicit confirmation for sensitive actions."},
        },
        "required": ["action"],
    },
    "handler": lambda parameters, **kwargs: handle_comm_action(parameters, **kwargs),
}


def handle_comm_action(parameters: dict, **kwargs) -> str:
    action = parameters.get("action", "").lower().strip()
    agent = CommunicationAgent()
    store = get_comm_store()

    # 1. Open Communication Dashboard
    if action == "open_comm_dashboard":
        _notify_comm_ui("comm_dashboard", {"action": "open"})
        devices = store.get_devices()
        active = store.get_active_call()
        dev_str = ", ".join(f"{d.name} ({d.status})" for d in devices)
        act_str = f"Active Call: {active.caller_name} [{active.state}]" if active else "No active call."
        return f"Opening Communication Dashboard.\nPaired Devices: {dev_str}\n{act_str}"

    # 2. Outgoing Call / Convey Message
    elif action in ("call_contact", "convey_message"):
        res = agent.handle(action, parameters)
        _notify_comm_ui("call_update", res.data or {})
        return res.message

    # 3. Send Message (WhatsApp / SMS)
    elif action == "send_message":
        res = agent.handle("send_message", parameters)
        _notify_comm_ui("message_sent", res.data or {})
        return res.message

    # 4. Answer Call
    elif action == "answer_call":
        res = agent.handle("answer_call", parameters)
        _notify_comm_ui("call_update", res.data or {})
        return res.message

    # 5. Screen Call
    elif action == "screen_call":
        res = agent.handle("screen_call", parameters)
        _notify_comm_ui("call_update", res.data or {})
        return res.message

    # 6. Transfer Call (Laptop <-> Phone)
    elif action == "transfer_call":
        active = store.get_active_call()
        if not active:
            return "No active call available to transfer."
        store.update_call_state(CallState.TRANSFER_REQUESTED)
        _notify_comm_ui("call_transferred", {"call_id": active.id})
        return f"Call with {active.caller_name} has been transferred to Sharu's Phone."

    # 7. End Call
    elif action == "end_call":
        res = agent.handle("end_call", parameters)
        _notify_comm_ui("call_ended", res.data or {})
        return res.message

    # 8. Recent Calls / Messages
    elif action == "get_recent_calls":
        res = agent.handle("recent_calls", parameters)
        return res.message

    elif action == "get_recent_messages":
        res = agent.handle("recent_messages", parameters)
        return res.message

    # 9. Resolve Contact
    elif action == "resolve_contact":
        res = agent.handle("resolve_contact", parameters)
        return res.message

    # 10. Set Call Handling Mode
    elif action == "set_handling_mode":
        mode = parameters.get("mode", CallHandlingMode.ASSISTANT).upper().strip()
        store.update_settings(call_handling_mode=mode)
        _notify_comm_ui("settings_updated", {"mode": mode})
        return f"Call handling mode set to: {mode}."

    return f"Executed communication action '{action}'."
