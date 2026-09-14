"""
flashcards.py — spaced-repetition flashcards for JARVIS
Drop into plugins/. Stores cards in memory/flashcards.json.

Simple Leitner-style spacing: each card has a "box" (0-4). Answering
correctly moves it to the next box (longer interval before it's due
again); answering "again"/incorrectly resets it to box 0 (due tomorrow).
Good for exam prep: "add a flashcard: front is TCP vs UDP, back is ..."
then later "review my flashcards".
"""

import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta

DATA_PATH = Path(__file__).resolve().parent.parent / "memory" / "flashcards.json"

BOX_INTERVALS_DAYS = [1, 3, 7, 14, 30]  # box 0..4

PLUGIN = {
    "name": "flashcards",
    "description": (
        "Create and review spaced-repetition flashcards for studying. "
        "Trigger phrases: 'add a flashcard...', 'review my flashcards', "
        "'quiz me with flashcards', 'the answer is...'/'I got it right/wrong' "
        "while reviewing, 'how many flashcards are due'. Use quiz_mode "
        "instead for AI-generated multiple-choice quizzes on a topic — "
        "this tool is for the user's own hand-written cards."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["add", "review", "answer", "due_count", "list"],
                "description": "add a card, start/continue reviewing due cards, grade the current card, count due cards, or list all cards.",
            },
            "front": {"type": "STRING", "description": "Question/prompt side (required for 'add')."},
            "back": {"type": "STRING", "description": "Answer side (required for 'add')."},
            "quality": {
                "type": "STRING",
                "enum": ["again", "hard", "good", "easy"],
                "description": "How well the user recalled the current card (required for 'answer').",
            },
        },
        "required": ["action"],
    },
}

_current_card_id = {"id": None}


def _load():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _save(cards):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(cards, indent=2), encoding="utf-8")


def _add(front, back):
    cards = _load()
    card = {
        "id": uuid.uuid4().hex[:8],
        "front": front,
        "back": back,
        "box": 0,
        "next_due": datetime.now().isoformat(),
    }
    cards.append(card)
    _save(cards)
    return f"Added flashcard: '{front}'. It's due for review right away."


def _due_cards():
    cards = _load()
    now = datetime.now()
    return [c for c in cards if datetime.fromisoformat(c["next_due"]) <= now]


def _review():
    due = _due_cards()
    if not due:
        return "No flashcards are due right now — nice and caught up."
    card = due[0]
    _current_card_id["id"] = card["id"]
    return f"({len(due)} due) {card['front']}"


def _answer(quality):
    if not _current_card_id["id"]:
        return "No card is currently being reviewed. Say 'review my flashcards' first."

    cards = _load()
    card = next((c for c in cards if c["id"] == _current_card_id["id"]), None)
    if not card:
        _current_card_id["id"] = None
        return "That card no longer exists."

    if quality in ("again", "hard"):
        card["box"] = 0
    else:  # "good" or "easy"
        card["box"] = min(card["box"] + 1, len(BOX_INTERVALS_DAYS) - 1)

    interval = BOX_INTERVALS_DAYS[card["box"]]
    card["next_due"] = (datetime.now() + timedelta(days=interval)).isoformat()
    _save(cards)

    answer_text = f"The answer was: {card['back']}. Next review in {interval} day(s)."
    _current_card_id["id"] = None

    remaining = _due_cards()
    if remaining:
        next_card = remaining[0]
        _current_card_id["id"] = next_card["id"]
        return f"{answer_text} Next card: {next_card['front']}"
    return f"{answer_text} That's all the due cards for now."


def _due_count():
    n = len(_due_cards())
    return f"You have {n} flashcard(s) due for review." if n else "No flashcards are due right now."


def _list():
    cards = _load()
    if not cards:
        return "You don't have any flashcards yet."
    return f"You have {len(cards)} flashcard(s) total, {len(_due_cards())} due right now."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    front = parameters.get("front")
    back = parameters.get("back")
    quality = parameters.get("quality")

    try:
        if action == "add":
            result_text = (
                "I need both a front and a back to add a flashcard."
                if not (front and back)
                else _add(front, back)
            )
        elif action == "review":
            result_text = _review()
        elif action == "answer":
            result_text = "How did you do — again, hard, good, or easy?" if not quality else _answer(quality)
        elif action == "due_count":
            result_text = _due_count()
        elif action == "list":
            result_text = _list()
        else:
            result_text = f"Sir, I don't recognize the flashcards action '{action}'."
    except Exception as e:
        return f"Sir, flashcards plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text