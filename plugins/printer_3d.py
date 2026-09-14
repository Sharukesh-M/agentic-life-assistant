"""
printer_3d.py — control a 3D printer via OctoPrint's REST API
Drop into plugins/. Requires config/api_keys.json to contain:
{
    "octoprint": {
        "base_url": "http://octopi.local",
        "api_key": "your OctoPrint API key from Settings -> API"
    }
}
"""

import json
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

PLUGIN = {
    "name": "printer_3d",
    "description": (
        "Check 3D print job status/progress, or pause/resume/cancel the "
        "current print via OctoPrint. Trigger phrases: 'how's the print "
        "going', 'pause the print', 'resume printing', 'cancel the print job'. "
        "This only controls an OctoPrint-connected 3D printer — unrelated to "
        "any regular document/photo printer."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["status", "pause", "resume", "cancel"],
                "description": "What to do with the current print job.",
            },
        },
        "required": ["action"],
    },
}


def _load_octoprint_config():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = data.get("octoprint")
    if not cfg or not cfg.get("base_url") or not cfg.get("api_key"):
        raise RuntimeError("No OctoPrint config found in config/api_keys.json.")
    return cfg


def _headers(cfg):
    return {"X-Api-Key": cfg["api_key"], "Content-Type": "application/json"}


def _status(cfg):
    resp = requests.get(f"{cfg['base_url']}/api/job", headers=_headers(cfg), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    state = data.get("state", "Unknown")
    progress = data.get("progress", {}).get("completion")
    file_name = data.get("job", {}).get("file", {}).get("name")

    if state == "Printing" and progress is not None:
        return f"Printing '{file_name}' — {progress:.1f}% complete."
    return f"Printer state: {state}."


def _job_command(cfg, command, action=None):
    payload = {"command": command}
    if action:
        payload["action"] = action
    resp = requests.post(f"{cfg['base_url']}/api/job", headers=_headers(cfg), json=payload, timeout=10)
    resp.raise_for_status()


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")

    try:
        cfg = _load_octoprint_config()
        if action == "status":
            result_text = _status(cfg)
        elif action == "pause":
            _job_command(cfg, "pause", "pause")
            result_text = "Print paused."
        elif action == "resume":
            _job_command(cfg, "pause", "resume")
            result_text = "Print resumed."
        elif action == "cancel":
            _job_command(cfg, "cancel")
            result_text = "Print job cancelled."
        else:
            result_text = f"Sir, I don't recognize the 3D printer action '{action}'."
    except requests.exceptions.RequestException as e:
        return f"Sir, I couldn't reach the printer: {e}"
    except Exception as e:
        return f"Sir, printer_3d plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text