"""
email_plugin.py — send and check email for JARVIS
Drop into plugins/.

Secrets (address + app password) come from environment variables, loaded
from a .env file in the project root — NOT from config/api_keys.json.
Add to .env (and make sure .env is in .gitignore):

    EMAIL_ADDRESS=you@gmail.com
    EMAIL_APP_PASSWORD=abcdefghijklmnop

Non-secret server hostnames can optionally still live in
config/api_keys.json under an "email" block, e.g.:
{
    "email": {
        "imap_server": "imap.gmail.com",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    }
}
If that block/file is missing, Gmail defaults are used automatically.

Gmail users: generate an "App Password" (not your normal password) at
https://myaccount.google.com/apppasswords — 2FA must be on for that page
to appear. Any other provider just needs its own IMAP/SMTP host+port.

Requires: pip install python-dotenv
"""

import os
import json
import smtplib
import imaplib
import email as email_lib
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root into os.environ

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

PLUGIN = {
    "name": "email_assistant",
    "description": (
        "Send an email on the user's behalf, or check how many unread emails "
        "are in the inbox. Trigger phrases: 'send an email to...', 'email ... "
        "and tell them...', 'check my email', 'do I have any unread emails'. "
        "Do NOT use send_message here — that tool is for WhatsApp/Telegram, "
        "this one is strictly for email."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["send", "check_unread"],
                "description": "Whether to send an email or check unread count.",
            },
            "to": {"type": "STRING", "description": "Recipient email address (required for 'send')."},
            "subject": {"type": "STRING", "description": "Email subject (required for 'send')."},
            "body": {"type": "STRING", "description": "Email body text (required for 'send')."},
        },
        "required": ["action"],
    },
}


def _load_email_config():
    address = os.getenv("EMAIL_ADDRESS")
    app_password = os.getenv("EMAIL_APP_PASSWORD")
    if not address or not app_password:
        raise RuntimeError(
            "EMAIL_ADDRESS / EMAIL_APP_PASSWORD not set — add them to your .env file."
        )

    # Non-secret server settings: optional, fall back to Gmail defaults.
    server_cfg = {}
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        server_cfg = data.get("email", {})

    return {
        "address": address,
        "app_password": app_password,
        "imap_server": server_cfg.get("imap_server", "imap.gmail.com"),
        "smtp_server": server_cfg.get("smtp_server", "smtp.gmail.com"),
        "smtp_port": server_cfg.get("smtp_port", 587),
    }


def _send(to, subject, body):
    cfg = _load_email_config()
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = cfg["address"]
    msg["To"] = to

    with smtplib.SMTP(cfg.get("smtp_server", "smtp.gmail.com"), cfg.get("smtp_port", 587)) as server:
        server.starttls()
        server.login(cfg["address"], cfg["app_password"])
        server.sendmail(cfg["address"], [to], msg.as_string())

    return f"Email sent to {to} with subject '{subject}'."


def _check_unread():
    cfg = _load_email_config()
    with imaplib.IMAP4_SSL(cfg.get("imap_server", "imap.gmail.com")) as imap:
        imap.login(cfg["address"], cfg["app_password"])
        imap.select("INBOX")
        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            return "Couldn't check the inbox right now."
        unread_ids = data[0].split()
        count = len(unread_ids)

        if count == 0:
            return "Your inbox is all caught up — no unread emails."

        latest_subject = None
        if unread_ids:
            status, msg_data = imap.fetch(unread_ids[-1], "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
            if status == "OK" and msg_data and msg_data[0]:
                raw = msg_data[0][1].decode(errors="ignore")
                latest_subject = email_lib.message_from_string(raw).get("Subject", "").strip()

        if latest_subject:
            return f"You have {count} unread email(s). Most recent: '{latest_subject}'."
        return f"You have {count} unread email(s)."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    to = parameters.get("to")
    subject = parameters.get("subject")
    body = parameters.get("body")

    try:
        if action == "send":
            if not (to and subject and body):
                result_text = "Sir, I need a recipient, subject, and body to send that email."
            else:
                result_text = _send(to, subject, body)
        elif action == "check_unread":
            result_text = _check_unread()
        else:
            result_text = f"Sir, I don't recognize the email action '{action}'."
    except Exception as e:
        return f"Sir, email_assistant failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text
