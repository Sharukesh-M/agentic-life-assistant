"""
memory/comm_store.py — JARVIS-X Communication, Contacts & Call State Management

Tracks:
- Authorized Device Registry (Laptop, Mobile Phone, Bridge)
- Contact Book & Resolution
- Call State Machine (IDLE, INCOMING, OUTGOING, CONNECTED, AI_SPEAKING, etc.)
- Call Logs & AI Summaries
- Message Logs (WhatsApp, SMS, App)
- Permissions & Handling Policies (MANUAL, SCREENING, ASSISTANT, FULL_DELEGATION)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import sys

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

COMM_DATA_PATH = _get_base_dir() / "memory" / "comm_data.json"
_lock = Lock()


# ---------------------------------------------------------------------------
# Call State Constants
# ---------------------------------------------------------------------------

class CallState:
    IDLE               = "IDLE"
    INCOMING_RINGING   = "INCOMING_RINGING"
    OUTGOING_DIALING   = "OUTGOING_DIALING"
    CONNECTING         = "CONNECTING"
    CONNECTED          = "CONNECTED"
    AI_SPEAKING        = "AI_SPEAKING"
    CALLER_SPEAKING    = "CALLER_SPEAKING"
    LISTENING          = "LISTENING"
    PROCESSING         = "PROCESSING"
    AI_RESPONDING      = "AI_RESPONDING"
    ON_HOLD            = "ON_HOLD"
    TRANSFER_REQUESTED = "TRANSFER_REQUESTED"
    ENDED              = "ENDED"
    FAILED             = "FAILED"


class CallHandlingMode:
    MANUAL          = "MANUAL"
    SCREENING       = "SCREENING"
    ASSISTANT       = "ASSISTANT"
    FULL_DELEGATION = "FULL_DELEGATION"


class MessageStatus:
    REQUESTED  = "REQUESTED"
    PREPARING  = "PREPARING"
    EXECUTING  = "EXECUTING"
    CONNECTED  = "CONNECTED"
    SENT       = "SENT"
    DELIVERED  = "DELIVERED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class DeviceRecord:
    id: str
    name: str
    type: str                     # "laptop" | "mobile_phone" | "bridge"
    status: str = "online"         # "online" | "offline" | "pairing"
    user_id: str = "user_default"
    platform: str = "Android"
    model_name: str = "iQOO Neo 10R"
    app_version: str = "1.0.0"
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    battery_level: int = 85
    charging_state: bool = True
    network_type: str = "Wi-Fi"
    bluetooth_status: str = "connected"         # "connected" | "disconnected"
    jarvis_connection_status: str = "online"     # "online" | "offline"
    authentication_state: str = "authenticated"   # "authenticated" | "unauthenticated" | "pairing"
    lock_status: str = "UNLOCKED"                 # "LOCKED" | "UNLOCKED"
    call_capability: bool = True
    call_permission: str = "granted"             # "granted" | "denied" | "not_requested"
    auth_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    capabilities: list[str] = field(default_factory=lambda: [
        "make_call", "contacts", "call_state", "notifications", "send_sms", "call_audio", "app_launch"
    ])
    permissions: dict[str, bool] = field(default_factory=lambda: {
        "PHONE_CALLS": True,
        "CONTACTS": True,
        "CALL_ANSWER": True,
        "CALL_END": True,
        "CALL_AUDIO": True,
        "CALL_TRANSCRIPTION": True,
        "MESSAGING": True,
        "NOTIFICATIONS": True,
        "APP_LAUNCH": True,
        "LOCATION": False,
        "CAMERA": False,
        "MICROPHONE": True
    })

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceRecord":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        safe = {k: v for k, v in d.items() if k in known}
        if isinstance(safe.get("permissions"), list):
            p_dict = {
                "PHONE_CALLS": "phone_calls" in safe["permissions"],
                "CONTACTS": "contacts" in safe["permissions"],
                "CALL_ANSWER": "call_handling" in safe["permissions"] or "phone_calls" in safe["permissions"],
                "CALL_END": True,
                "CALL_AUDIO": True,
                "CALL_TRANSCRIPTION": True,
                "MESSAGING": "messages" in safe["permissions"] or "whatsapp" in safe["permissions"],
                "NOTIFICATIONS": "notifications" in safe["permissions"],
                "APP_LAUNCH": True,
                "LOCATION": False,
                "CAMERA": False,
                "MICROPHONE": "microphone" in safe["permissions"]
            }
            safe["permissions"] = p_dict
        return cls(**safe)


@dataclass
class ContactRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:6])
    name: str = ""
    phone: str = ""
    whatsapp_id: str = ""
    relationship: str = ""        # e.g. "Friend", "Mom", "Colleague"
    preferred_channel: str = "whatsapp"
    is_favorite: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CallRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    caller_name: str = ""
    caller_phone: str = ""
    direction: str = "incoming"   # "incoming" | "outgoing"
    state: str = CallState.IDLE
    handling_mode: str = CallHandlingMode.ASSISTANT
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    duration_seconds: int = 0
    message_to_convey: str = ""   # text JARVIS was instructed to convey
    transcript: list[dict] = field(default_factory=list) # [{"speaker": "AI/Caller", "text": "..."}]
    summary: str = ""
    follow_up_tasks: list[str] = field(default_factory=list)
    transferred_to_user: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MessageRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    recipient_name: str = ""
    recipient_phone: str = ""
    channel: str = "whatsapp"     # "whatsapp" | "sms" | "telegram"
    content: str = ""
    status: str = MessageStatus.SENT
    is_sensitive: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# CommStore Manager
# ---------------------------------------------------------------------------

class CommStore:
    """Thread-safe storage for cross-device communications, contacts, and calls."""

    def __init__(self, path: Path = COMM_DATA_PATH):
        self._path = path
        self._lock = Lock()
        self._pairing_sessions: dict[str, dict] = {}
        self._ensure_default_seed()

    def _load_raw(self) -> dict:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[CommStore] Load error: {e}")
        return self._default_structure()

    def _save_raw(self, data: dict) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"[CommStore] Save error: {e}")

    def _default_structure(self) -> dict:
        return {
            "devices": [
                {
                    "id": "dev_laptop_1",
                    "name": "Sharu's Laptop (Mac)",
                    "type": "laptop",
                    "status": "online",
                    "user_id": "user_default",
                    "platform": "macOS",
                    "model_name": "MacBook Pro",
                    "app_version": "2.4.0",
                    "last_seen": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                    "battery_level": 100,
                    "network_type": "Wi-Fi",
                    "bluetooth_status": "connected",
                    "jarvis_connection_status": "online",
                    "auth_token": "token_laptop_mac_001",
                    "authentication_state": "authenticated",
                    "call_capability": True,
                    "call_permission": "granted",
                    "capabilities": ["orchestrator", "voice", "gui", "task_engine"],
                    "permissions": {
                        "PHONE_CALLS": True, "CONTACTS": True, "CALL_ANSWER": True,
                        "CALL_END": True, "CALL_AUDIO": True, "CALL_TRANSCRIPTION": True,
                        "MESSAGING": True, "NOTIFICATIONS": True, "APP_LAUNCH": True,
                        "LOCATION": True, "CAMERA": True, "MICROPHONE": True
                    }
                },
                {
                    "id": "dev_phone_1",
                    "name": "iQOO Neo 10R",
                    "type": "mobile_phone",
                    "status": "online",
                    "user_id": "user_default",
                    "platform": "Android 14",
                    "model_name": "iQOO Neo 10R",
                    "app_version": "1.0.0",
                    "last_seen": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                    "battery_level": 88,
                    "network_type": "Wi-Fi",
                    "bluetooth_status": "connected",
                    "jarvis_connection_status": "online",
                    "auth_token": "token_android_phone_889",
                    "authentication_state": "authenticated",
                    "call_capability": True,
                    "call_permission": "granted",
                    "capabilities": ["make_call", "contacts", "call_state", "notifications", "send_sms", "call_audio", "app_launch"],
                    "permissions": {
                        "PHONE_CALLS": True, "CONTACTS": True, "CALL_ANSWER": True,
                        "CALL_END": True, "CALL_AUDIO": True, "CALL_TRANSCRIPTION": True,
                        "MESSAGING": True, "NOTIFICATIONS": True, "APP_LAUNCH": True,
                        "LOCATION": False, "CAMERA": False, "MICROPHONE": True
                    }
                }
            ],
            "contacts": [
                {"id": "c1", "name": "Arun", "phone": "+919876543210", "relationship": "Friend", "preferred_channel": "whatsapp"},
                {"id": "c2", "name": "Mom", "phone": "+919876543211", "relationship": "Family", "preferred_channel": "whatsapp", "is_favorite": True},
                {"id": "c3", "name": "Dad", "phone": "+919876543212", "relationship": "Family", "preferred_channel": "whatsapp", "is_favorite": True},
                {"id": "c4", "name": "Priya", "phone": "+919876543213", "relationship": "Colleague", "preferred_channel": "whatsapp"},
                {"id": "c5", "name": "Shyam", "phone": "+919876543299", "relationship": "Friend", "preferred_channel": "cellular"}
            ],
            "active_call": None,
            "calls_history": [],
            "messages_history": [],
            "settings": {
                "call_handling_mode": CallHandlingMode.ASSISTANT,
                "unknown_caller_policy": "SCREEN",
                "require_sensitive_confirmation": True
            }
        }

    def _ensure_default_seed(self):
        if not self._path.exists():
            self._save_raw(self._default_structure())

    # ── Contact Operations ───────────────────────────────────────────────────

    def resolve_contact(self, name_query: str) -> list[ContactRecord]:
        """Find matching contacts by name (case-insensitive substring)."""
        q = name_query.strip().lower()
        if not q:
            return []
        with self._lock:
            data = self._load_raw()
            matches = []
            for c in data.get("contacts", []):
                if q in c["name"].lower() or q in c.get("relationship", "").lower():
                    matches.append(ContactRecord(**c))
            return matches

    def add_contact(self, contact: ContactRecord) -> ContactRecord:
        with self._lock:
            data = self._load_raw()
            data.setdefault("contacts", []).append(contact.to_dict())
            self._save_raw(data)
            return contact

    # ── Call Operations ──────────────────────────────────────────────────────

    def get_active_call(self) -> Optional[CallRecord]:
        with self._lock:
            data = self._load_raw()
            raw = data.get("active_call")
            return CallRecord(**raw) if raw else None

    def start_call(self, caller_name: str, caller_phone: str, direction: str = "outgoing", message_to_convey: str = "") -> CallRecord:
        with self._lock:
            data = self._load_raw()
            call = CallRecord(
                caller_name=caller_name,
                caller_phone=caller_phone,
                direction=direction,
                state=CallState.OUTGOING_DIALING if direction == "outgoing" else CallState.INCOMING_RINGING,
                message_to_convey=message_to_convey
            )
            data["active_call"] = call.to_dict()
            self._save_raw(data)
            return call

    def update_call_state(self, new_state: str, transcript_line: dict | None = None) -> Optional[CallRecord]:
        with self._lock:
            data = self._load_raw()
            raw = data.get("active_call")
            if not raw:
                return None
            call = CallRecord(**raw)
            call.state = new_state
            if transcript_line:
                call.transcript.append(transcript_line)
            data["active_call"] = call.to_dict()
            self._save_raw(data)
            return call

    def end_call(self, summary: str = "", follow_up_tasks: list[str] | None = None) -> Optional[CallRecord]:
        with self._lock:
            data = self._load_raw()
            raw = data.get("active_call")
            if not raw:
                return None
            call = CallRecord(**raw)
            call.state = CallState.ENDED
            call.end_time = datetime.now().isoformat()
            call.summary = summary or f"Call with {call.caller_name} ended."
            call.follow_up_tasks = follow_up_tasks or []
            
            data["calls_history"].insert(0, call.to_dict())
            data["active_call"] = None
            self._save_raw(data)
            return call

    def get_recent_calls(self, limit: int = 10) -> list[CallRecord]:
        with self._lock:
            data = self._load_raw()
            return [CallRecord(**c) for c in data.get("calls_history", [])[:limit]]

    # ── Message Operations ───────────────────────────────────────────────────

    def log_message(self, msg: MessageRecord) -> MessageRecord:
        with self._lock:
            data = self._load_raw()
            data.setdefault("messages_history", []).insert(0, msg.to_dict())
            self._save_raw(data)
            return msg

    def get_recent_messages(self, limit: int = 10) -> list[MessageRecord]:
        with self._lock:
            data = self._load_raw()
            return [MessageRecord(**m) for m in data.get("messages_history", [])[:limit]]

    # ── Device & Settings Operations ─────────────────────────────────────────

    def get_devices(self) -> list[DeviceRecord]:
        with self._lock:
            data = self._load_raw()
            return [DeviceRecord.from_dict(d) for d in data.get("devices", [])]

    def get_phone_device(self) -> Optional[DeviceRecord]:
        devices = self.get_devices()
        phones = [d for d in devices if d.type == "mobile_phone" and d.status == "online"]
        if phones:
            return phones[0]
        all_phones = [d for d in devices if d.type == "mobile_phone"]
        return all_phones[0] if all_phones else None

    def resolve_device(self, device_query: str = "") -> dict:
        devices = self.get_devices()
        mobile_devices = [d for d in devices if d.type == "mobile_phone"]
        
        target = None
        if device_query:
            q = device_query.lower().strip()
            for d in mobile_devices:
                if q in d.name.lower() or q in d.model_name.lower() or q in d.id.lower():
                    target = d
                    break
        
        if not target:
            online_phones = [d for d in mobile_devices if d.status == "online" or d.jarvis_connection_status == "online"]
            if len(online_phones) == 1:
                target = online_phones[0]
            elif len(online_phones) > 1:
                return {
                    "valid": False,
                    "error_code": "MULTIPLE_PHONES_CONNECTED",
                    "error": f"You have {len(online_phones)} phones connected. Which one should I use?"
                }
            elif mobile_devices:
                target = mobile_devices[0]

        if not target:
            return {
                "valid": False,
                "error_code": "NO_PHONE_REGISTERED",
                "error": "No Android phone is paired with JARVIS-X."
            }

        # Validate state progression
        if target.jarvis_connection_status != "online" and target.status != "online":
            return {
                "valid": False,
                "device": target,
                "error_code": "PHONE_OFFLINE",
                "error": f"My phone bridge is offline ({target.name}), so I can't place that call."
            }

        if target.authentication_state != "authenticated":
            return {
                "valid": False,
                "device": target,
                "error_code": "UNAUTHENTICATED_DEVICE",
                "error": f"The device '{target.name}' is paired but not authenticated."
            }

        if not target.call_capability or "make_call" not in target.capabilities:
            return {
                "valid": False,
                "device": target,
                "error_code": "CAPABILITY_MISSING",
                "error": f"Device '{target.name}' does not support phone calling capabilities."
            }

        perm_granted = bool(target.permissions.get("PHONE_CALLS", False)) and target.call_permission == "granted"
        if not perm_granted:
            return {
                "valid": False,
                "device": target,
                "error_code": "PERMISSION_DENIED",
                "error": f"I need phone-call permission on your {target.name} before I can place calls."
            }

        return {
            "valid": True,
            "device": target
        }

    def create_pairing_token(self, ttl_seconds: int = 300) -> dict:
        token = f"pair_{uuid.uuid4().hex[:12]}"
        session_id = uuid.uuid4().hex[:8]
        expires_at = datetime.fromtimestamp(datetime.now().timestamp() + ttl_seconds).isoformat()
        payload = {
            "version": "1.0",
            "session_id": session_id,
            "pairing_token": token,
            "server_endpoint": "ws://localhost:8000/ws/phone_bridge",
            "expires_at": expires_at,
            "challenge": uuid.uuid4().hex[:16]
        }
        self._pairing_sessions[token] = payload
        return payload

    def verify_pairing_token(self, token: str, device_name: str, platform: str = "Android 14") -> dict:
        if token not in self._pairing_sessions:
            # For testing/demo fallback, accept pairing tokens matching prefix or active requests
            if token.startswith("pair_") or token == "demo_pair":
                dev_id = f"dev_phone_{uuid.uuid4().hex[:4]}"
                token_val = uuid.uuid4().hex
                dev = DeviceRecord(
                    id=dev_id,
                    name=device_name or "Android Companion Phone",
                    type="mobile_phone",
                    status="online",
                    platform=platform,
                    auth_token=token_val,
                    authentication_state="authenticated"
                )
                self.add_or_update_device(dev)
                return {"success": True, "device_id": dev_id, "auth_token": token_val, "device": dev.to_dict()}
            return {"success": False, "error": "Invalid or expired pairing token."}

        sess = self._pairing_sessions.pop(token)
        dev_id = f"dev_phone_{uuid.uuid4().hex[:4]}"
        token_val = uuid.uuid4().hex
        dev = DeviceRecord(
            id=dev_id,
            name=device_name or "Android Companion Phone",
            type="mobile_phone",
            status="online",
            platform=platform,
            auth_token=token_val,
            authentication_state="authenticated"
        )
        self.add_or_update_device(dev)
        return {"success": True, "device_id": dev_id, "auth_token": token_val, "device": dev.to_dict()}

    def add_or_update_device(self, device: DeviceRecord) -> DeviceRecord:
        with self._lock:
            data = self._load_raw()
            devs = data.get("devices", [])
            idx = next((i for i, d in enumerate(devs) if d["id"] == device.id), None)
            if idx is not None:
                devs[idx] = device.to_dict()
            else:
                devs.append(device.to_dict())
            data["devices"] = devs
            self._save_raw(data)
            return device

    def update_device_status(self, device_id: str, status: str = "online", battery_level: int | None = None, network_type: str | None = None) -> Optional[DeviceRecord]:
        with self._lock:
            data = self._load_raw()
            devs = data.get("devices", [])
            target = None
            for d in devs:
                if d["id"] == device_id or (device_id == "mobile_phone" and d.get("type") == "mobile_phone"):
                    d["status"] = status
                    d["last_seen"] = datetime.now().isoformat()
                    d["last_active"] = datetime.now().isoformat()
                    if battery_level is not None:
                        d["battery_level"] = battery_level
                    if network_type is not None:
                        d["network_type"] = network_type
                    target = d
                    break
            if target:
                self._save_raw(data)
                return DeviceRecord.from_dict(target)
            return None

    def update_device_permission(self, device_id: str, perm_name: str, granted: bool) -> Optional[DeviceRecord]:
        with self._lock:
            data = self._load_raw()
            devs = data.get("devices", [])
            target = None
            for d in devs:
                if d["id"] == device_id or (device_id == "mobile_phone" and d.get("type") == "mobile_phone"):
                    perms = d.get("permissions", {})
                    if isinstance(perms, list):
                        perms = {p: True for p in perms}
                    perms[perm_name.upper()] = bool(granted)
                    d["permissions"] = perms
                    d["last_active"] = datetime.now().isoformat()
                    target = d
                    break
            if target:
                self._save_raw(data)
                return DeviceRecord.from_dict(target)
            return None

    def get_settings(self) -> dict:
        with self._lock:
            data = self._load_raw()
            return data.get("settings", {
                "call_handling_mode": CallHandlingMode.ASSISTANT,
                "unknown_caller_policy": "SCREEN",
                "require_sensitive_confirmation": True
            })

    def update_settings(self, **kwargs) -> dict:
        with self._lock:
            data = self._load_raw()
            s = data.get("settings", {})
            for k, v in kwargs.items():
                s[k] = v
            data["settings"] = s
            self._save_raw(data)
            return s


_default_comm_store: Optional[CommStore] = None
_comm_lock = Lock()

def get_comm_store() -> CommStore:
    global _default_comm_store
    if _default_comm_store is None:
        with _comm_lock:
            if _default_comm_store is None:
                _default_comm_store = CommStore()
    return _default_comm_store
