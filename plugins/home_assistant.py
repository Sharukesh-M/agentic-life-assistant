"""
home_assistant.py — control Home Assistant (home-assistant.io) devices from JARVIS
Drop into plugins/. Requires config/api_keys.json to contain:
{
    "home_assistant": {
        "base_url": "http://homeassistant.local:8123",
        "token": "long-lived access token from your HA profile page"
    }
}
Generate the token in Home Assistant: Profile -> Security -> Long-Lived
Access Tokens -> Create Token.
"""

import json
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

PLUGIN = {
    "name": "home_assistant",
    "description": (
        "Control smart home devices through Home Assistant — turn things "
        "on/off, toggle, or read a sensor's state. Trigger phrases: 'turn on "
        "the...', 'turn off the...', 'what's the temperature in...'. Do NOT "
        "use computer_settings for this — that tool controls the PC itself "
        "(volume, brightness, WiFi), this one controls the smart home."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["turn_on", "turn_off", "toggle", "get_state"],
                "description": "The action to perform on the entity.",
            },
            "entity_id": {
                "type": "STRING",
                "description": "Home Assistant entity id, e.g. 'light.living_room' or 'sensor.bedroom_temperature'.",
            },
        },
        "required": ["action", "entity_id"],
    },
}


def _load_ha_config():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = data.get("home_assistant")
    if not cfg or not cfg.get("base_url") or not cfg.get("token"):
        raise RuntimeError("No Home Assistant config found in config/api_keys.json.")
    return cfg


def _headers(cfg):
    return {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}


def _call_service(cfg, domain, service, entity_id):
    url = f"{cfg['base_url']}/api/services/{domain}/{service}"
    resp = requests.post(url, headers=_headers(cfg), json={"entity_id": entity_id}, timeout=10)
    resp.raise_for_status()


def _get_state(cfg, entity_id):
    url = f"{cfg['base_url']}/api/states/{entity_id}"
    resp = requests.get(url, headers=_headers(cfg), timeout=10)
    resp.raise_for_status()
    return resp.json()


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    entity_id = parameters.get("entity_id", "")

    try:
        if not entity_id:
            result_text = "Sir, I need to know which device — the entity id was empty."
        else:
            cfg = _load_ha_config()
            domain = entity_id.split(".")[0]

            if action in ("turn_on", "turn_off", "toggle"):
                _call_service(cfg, domain, action, entity_id)
                friendly = entity_id.split(".")[-1].replace("_", " ")
                result_text = f"Done — {friendly} {action.replace('_', ' ')}."
            elif action == "get_state":
                state = _get_state(cfg, entity_id)
                friendly = state.get("attributes", {}).get("friendly_name", entity_id)
                unit = state.get("attributes", {}).get("unit_of_measurement", "")
                result_text = f"{friendly} is currently {state.get('state')} {unit}".strip()
            else:
                result_text = f"Sir, I don't recognize the home assistant action '{action}'."
    except requests.exceptions.RequestException as e:
        return f"Sir, I couldn't reach Home Assistant: {e}"
    except Exception as e:
        return f"Sir, home_assistant plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text