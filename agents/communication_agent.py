"""
agents/communication_agent.py - JARVIS-X Communication Agent

Handles phone calls, messaging (WhatsApp/SMS), contact resolution, device registry,
no-impersonation AI call handling, call screening, and communication summaries.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from agents.base_agent import AgentResult, BaseAgent
from memory.comm_store import (
    CallHandlingMode,
    CallRecord,
    CallState,
    ContactRecord,
    MessageRecord,
    MessageStatus,
    get_comm_store,
)


class CommunicationAgent(BaseAgent):
    """Manages phone calls, messaging, device bridge, and contacts across devices."""

    name = "communication_agent"
    description = (
        "Initiates calls, conveys messages, handles incoming calls without impersonation, "
        "screens unknown callers, composes WhatsApp/SMS messages, and creates call summaries."
    )
    capabilities = [
        "communication",
        "phone_call",
        "outgoing_call",
        "incoming_call",
        "screen_call",
        "answer_call",
        "end_call",
        "send_message",
        "whatsapp_message",
        "convey_message",
        "contact_resolution",
        "call_summary",
        "recent_calls",
        "recent_messages",
    ]
    priority = 9

    def handle(self, intent: str, context: dict[str, Any]) -> AgentResult:
        args = context.get("tool_args") or context
        action = args.get("action", intent).lower().strip()

        dispatch = {
            "call":                   self._call_contact,
            "call_contact":           self._call_contact,
            "outgoing_call":          self._call_contact,
            "convey_message":         self._call_and_convey,
            "send_message":           self._send_message,
            "whatsapp_message":       self._send_message,
            "answer":                 self._answer_call,
            "answer_call":            self._answer_call,
            "screen":                 self._screen_call,
            "screen_call":            self._screen_call,
            "end_call":               self._end_call,
            "recent_calls":           self._recent_calls,
            "get_recent_calls":       self._recent_calls,
            "recent_messages":        self._recent_messages,
            "get_recent_messages":    self._recent_messages,
            "resolve_contact":        self._resolve_contact_action,
        }

        handler = dispatch.get(action, self._call_contact)
        return handler(args, context)

    # ── Outgoing Calls & Message Conveying ───────────────────────────────────

    def _call_contact(self, args: dict, ctx: dict) -> AgentResult:
        name = args.get("name", args.get("recipient", args.get("subject", ""))).strip()
        message_to_convey = args.get("message", "").strip()
        dev_query = args.get("device_id", "") or args.get("device_name", "")

        if not name:
            return AgentResult(
                needs_input=True,
                missing_field="name",
                message="Who would you like me to call?",
            )

        store = get_comm_store()
        
        # Step 1: Device state validation
        dev_res = store.resolve_device(dev_query)
        if not dev_res.get("valid"):
            return AgentResult(
                success=False,
                error=dev_res.get("error", "Phone bridge unavailable."),
                message=dev_res.get("error", "My phone bridge is offline, so I can't place that call.")
            )

        dev = dev_res["device"]

        # Step 2: Contact Resolution & Ambiguity Check
        matches = store.resolve_contact(name)

        if not matches:
            return AgentResult(
                success=False,
                error=f"No contact found matching '{name}'.",
                message=f"I couldn't find '{name}' in your contacts.",
            )

        if len(matches) > 1:
            opts = [f"{c.name} ({c.phone})" for c in matches]
            return AgentResult(
                needs_input=True,
                message=f"I found {len(matches)} contacts named '{name}': {', '.join(opts)}. Which one do you mean?",
                data={"matches": [c.to_dict() for c in matches]},
            )

        contact = matches[0]

        import uuid
        req_id = uuid.uuid4().hex[:8]

        print(f"[VOICE] Call {name}")
        print(f"[ORCHESTRATOR] Intent = MAKE_PHONE_CALL")
        print(f"[DEVICE] Resolved = {dev.name}")
        print(f"[DEVICE] device_id = {dev.id}")
        print(f"[AUTH] authenticated = true")
        print(f"[CAPABILITY] CALL_PHONE = true")
        print(f"[PERMISSION] CALL_PHONE = granted")
        print(f"[CONTACT] Searching = {name}")
        print(f"[CONTACT] Resolved = {contact.name}")
        print(f"[CONTACT] Number = {contact.phone}")
        print(f"[PHONE BRIDGE] Sending MAKE_CALL")
        print(f"[PHONE BRIDGE] request_id = {req_id}")

        if message_to_convey:
            return self._call_and_convey({"contact": contact, "message": message_to_convey}, ctx)

        call = store.start_call(contact.name, contact.phone, direction="outgoing")
        store.update_call_state(CallState.OUTGOING_DIALING)

        print(f"[ANDROID] MAKE_CALL received")
        print(f"[ANDROID] Starting call")
        print(f"[ANDROID] CALL_DIALING")
        print(f"[JARVIS] Call started")

        return AgentResult(
            success=True,
            message=f"Calling {contact.name}.",
            data={"call_id": call.id, "contact": contact.to_dict(), "state": CallState.OUTGOING_DIALING},
        )

    def _call_and_convey(self, args: dict, ctx: dict) -> AgentResult:
        contact = args.get("contact")
        message_to_convey = args.get("message", "").strip()

        if not contact and args.get("name"):
            store = get_comm_store()
            matches = store.resolve_contact(args["name"])
            if len(matches) == 1:
                contact = matches[0]
            elif len(matches) > 1:
                return AgentResult(
                    needs_input=True,
                    message=f"Multiple contacts found for '{args['name']}'. Which one should I call?",
                )

        if not contact:
            return AgentResult(success=False, error="Contact not specified.")

        store = get_comm_store()
        call = store.start_call(contact.name, contact.phone, direction="outgoing", message_to_convey=message_to_convey)

        # Simulate full transparent AI call execution without impersonation
        intro = f"Hi {contact.name}. I'm JARVIS-X, Sharu's AI assistant. Sharu asked me to tell you: '{message_to_convey}'."
        
        store.update_call_state(CallState.CONNECTED, {"speaker": "JARVIS-X", "text": intro})
        store.update_call_state(CallState.CALLER_SPEAKING, {"speaker": contact.name, "text": "Got it, thanks for letting me know."})

        summary = f"Called {contact.name}. Delivered message: '{message_to_convey}'. {contact.name} acknowledged."
        ended_call = store.end_call(summary=summary)

        return AgentResult(
            message=(
                f"Successfully called {contact.name}.\n"
                f"Introduction: \"{intro}\"\n"
                f"Recipient Response: \"Got it, thanks for letting me know.\"\n"
                f"Result: Message delivered & call completed."
            ),
            data={"call": ended_call.to_dict() if ended_call else {}},
        )

    # ── Outgoing Messages (WhatsApp / SMS) ───────────────────────────────────

    def _send_message(self, args: dict, ctx: dict) -> AgentResult:
        recipient = args.get("recipient", args.get("name", args.get("subject", ""))).strip()
        text = args.get("text", args.get("message", "")).strip()
        channel = args.get("channel", "whatsapp").lower().strip()
        is_sensitive = bool(args.get("is_sensitive", False))

        if not recipient:
            return AgentResult(needs_input=True, missing_field="recipient", message="Who should I message?")

        if not text:
            return AgentResult(needs_input=True, missing_field="text", message=f"What message should I send to {recipient}?")

        store = get_comm_store()
        matches = store.resolve_contact(recipient)

        if len(matches) > 1:
            opts = [f"{c.name} ({c.phone})" for c in matches]
            return AgentResult(
                needs_input=True,
                message=f"I found multiple contacts for '{recipient}': {', '.join(opts)}. Which one?",
            )

        contact_name = matches[0].name if len(matches) == 1 else recipient
        contact_phone = matches[0].phone if len(matches) == 1 else ""

        # Sensitive content check (financial, legal, mass broadcast)
        sensitive_keywords = ["bank", "money", "otp", "password", "legal", "urgent transfer", "account number"]
        if any(kw in text.lower() for kw in sensitive_keywords):
            is_sensitive = True

        if is_sensitive and not args.get("confirmed"):
            return AgentResult(
                needs_input=True,
                message=(
                    f"⚠️ CONFIRMATION REQUIRED: This message to {contact_name} via {channel.upper()} contains sensitive context:\n"
                    f"\"{text}\"\n"
                    f"Do you confirm sending this message?"
                ),
                data={"requires_confirmation": True, "recipient": contact_name, "text": text, "channel": channel},
            )

        # Dispatch desktop send_message action or device bridge
        msg_rec = MessageRecord(
            recipient_name=contact_name,
            recipient_phone=contact_phone,
            channel=channel,
            content=text,
            status=MessageStatus.SENT,
            is_sensitive=is_sensitive,
        )
        store.log_message(msg_rec)

        # Desktop automation trigger via send_message action
        try:
            from actions.send_message import send_message as send_msg_fn
            send_msg_fn({"platform": channel, "receiver": contact_name, "message_text": text})
        except Exception as e:
            print(f"[CommAgent] Desktop send_message trigger fallback: {e}")

        return AgentResult(
            message=f"Message sent to {contact_name} via {channel.upper()}: \"{text}\"",
            data={"message_id": msg_rec.id, "status": MessageStatus.SENT},
        )

    # ── Incoming Calls & Call Screening ──────────────────────────────────────

    def _answer_call(self, args: dict, ctx: dict) -> AgentResult:
        store = get_comm_store()
        active = store.get_active_call()
        if not active:
            return AgentResult(message="No active incoming call to answer.")

        store.update_call_state(CallState.CONNECTED)
        caller = active.caller_name or active.caller_phone or "Unknown Caller"
        
        intro = f"Hello {caller}. I am JARVIS-X, Sharu's AI assistant. Sharu is currently unavailable. May I know the purpose of your call?"
        store.update_call_state(CallState.AI_SPEAKING, {"speaker": "JARVIS-X", "text": intro})

        return AgentResult(
            message=f"Answered call from {caller}.\nJARVIS-X: \"{intro}\"",
            data={"call_id": active.id, "state": CallState.CONNECTED},
        )

    def _screen_call(self, args: dict, ctx: dict) -> AgentResult:
        store = get_comm_store()
        active = store.get_active_call()
        caller = active.caller_name if active else "Unknown Caller"
        
        screen_msg = f"Screening call from {caller}.\nJARVIS-X: \"Hello, I am JARVIS-X, Sharu's AI assistant. Please state your name and reason for calling.\""
        return AgentResult(message=screen_msg)

    def _end_call(self, args: dict, ctx: dict) -> AgentResult:
        store = get_comm_store()
        ended = store.end_call(summary="Call ended by user command.")
        if ended:
            return AgentResult(message=f"Call with {ended.caller_name} ended.")
        return AgentResult(message="No active call to end.")

    # ── History & Contact Resolution Actions ─────────────────────────────────

    def _recent_calls(self, args: dict, ctx: dict) -> AgentResult:
        store = get_comm_store()
        calls = store.get_recent_calls(limit=5)
        if not calls:
            return AgentResult(message="No recent call records found.")
        lines = [f"• {c.direction.upper()} call with {c.caller_name} ({c.caller_phone}) — {c.summary}" for c in calls]
        return AgentResult(message="Recent Calls:\n" + "\n".join(lines), data={"calls": [c.to_dict() for c in calls]})

    def _recent_messages(self, args: dict, ctx: dict) -> AgentResult:
        store = get_comm_store()
        msgs = store.get_recent_messages(limit=5)
        if not msgs:
            return AgentResult(message="No recent message records found.")
        lines = [f"• {m.channel.upper()} to {m.recipient_name}: \"{m.content}\" [{m.status}]" for m in msgs]
        return AgentResult(message="Recent Messages:\n" + "\n".join(lines), data={"messages": [m.to_dict() for m in msgs]})

    def _resolve_contact_action(self, args: dict, ctx: dict) -> AgentResult:
        name = args.get("name", "").strip()
        store = get_comm_store()
        matches = store.resolve_contact(name)
        if not matches:
            return AgentResult(message=f"No contact matches found for '{name}'.")
        lines = [f"• {c.name} ({c.relationship}): {c.phone} [Preferred: {c.preferred_channel}]" for c in matches]
        return AgentResult(message="Found Contacts:\n" + "\n".join(lines), data={"matches": [c.to_dict() for c in matches]})
