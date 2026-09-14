"""
quiz_mode.py — interactive quiz plugin for JARVIS
Drop into plugins/. Uses the same Gemini API key already configured for
the assistant (config/api_keys.json -> "gemini_api_key") to generate
quiz questions on any topic, then tracks score across a session.

Great fit for exam prep: "start a quiz on GATE operating systems"
"""

import json
import random
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
GEMINI_MODEL = "gemini-2.5-flash"

PLUGIN = {
    "name": "quiz_mode",
    "description": (
        "Run an interactive multiple-choice quiz on any topic — start a quiz, "
        "submit an answer, check score, or end the quiz. Trigger phrases: "
        "'quiz me on...', 'start a quiz about...', 'test me on...', "
        "'the answer is...' while a quiz is active. Do NOT use code_helper or "
        "file_processor for this — quiz_mode owns all Q&A/testing flows."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["start", "answer", "score", "end"],
                "description": "start a new quiz, submit an answer, check score, or end the quiz.",
            },
            "topic": {
                "type": "STRING",
                "description": "Topic for a new quiz (required for 'start'), e.g. 'GATE Computer Networks'.",
            },
            "num_questions": {"type": "INTEGER", "description": "How many questions, default 5."},
            "answer": {"type": "STRING", "description": "The user's spoken answer (required for 'answer')."},
        },
        "required": ["action"],
    },
}

# In-memory session state — single-user desktop assistant, so this is fine.
_session = {"questions": [], "index": 0, "score": 0, "topic": None}


def _get_api_key():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    key = data.get("gemini_api_key")
    if not key:
        raise RuntimeError("gemini_api_key missing from config/api_keys.json")
    return key


def _generate_questions(topic, n):
    key = _get_api_key()
    prompt = (
        f"Generate {n} multiple-choice quiz questions about '{topic}'. "
        "Respond ONLY as JSON: a list of objects with keys "
        "'question', 'options' (list of 4 strings), 'correct_index' (0-3), 'explanation'. "
        "No markdown, no extra text."
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={key}"
    )
    resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().strip("```json").strip("```").strip()
    return json.loads(text)


def _ask_current():
    q = _session["questions"][_session["index"]]
    opts_str = "; ".join(f"{chr(65 + i)}) {o}" for i, o in enumerate(q["options"]))
    return f"Question {_session['index'] + 1} of {len(_session['questions'])}: {q['question']} Options: {opts_str}"


def _start(topic, num_questions):
    n = num_questions or 5
    questions = _generate_questions(topic, n)
    random.shuffle(questions)
    _session.update({"questions": questions, "index": 0, "score": 0, "topic": topic})
    return _ask_current()


def _answer(user_answer):
    if not _session["questions"]:
        return "No quiz is running, sir. Say 'start a quiz on <topic>' first."

    q = _session["questions"][_session["index"]]
    options = q["options"]
    correct = options[q["correct_index"]]

    given = user_answer.strip().lower()
    is_correct = given == correct.strip().lower() or (
        given in ("a", "b", "c", "d") and options[ord(given) - ord("a")] == correct
    )

    if is_correct:
        _session["score"] += 1
        feedback = "Correct!"
    else:
        feedback = f"Not quite — the correct answer was: {correct}. {q.get('explanation', '')}"

    _session["index"] += 1
    if _session["index"] >= len(_session["questions"]):
        final = (
            f"{feedback} That's the quiz done — you scored {_session['score']} "
            f"out of {len(_session['questions'])} on {_session['topic']}."
        )
        _session.update({"questions": [], "index": 0})
        return final

    return f"{feedback} {_ask_current()}"


def _score():
    if not _session["questions"]:
        return "No quiz is currently running."
    return f"Score so far: {_session['score']} out of {_session['index']} answered."


def _end():
    if not _session["questions"]:
        return "No quiz is currently running."
    final = (
        f"Quiz ended early — you scored {_session['score']} out of "
        f"{_session['index']} answered on {_session['topic']}."
    )
    _session.update({"questions": [], "index": 0, "score": 0, "topic": None})
    return final


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    topic = parameters.get("topic")
    num_questions = parameters.get("num_questions")
    answer = parameters.get("answer")

    try:
        if action == "start":
            result_text = "What topic should the quiz be on, sir?" if not topic else _start(topic, num_questions)
        elif action == "answer":
            result_text = "I didn't catch an answer." if answer is None else _answer(answer)
        elif action == "score":
            result_text = _score()
        elif action == "end":
            result_text = _end()
        else:
            result_text = f"Sir, I don't recognize the quiz action '{action}'."
    except Exception as e:
        return f"Sir, quiz_mode failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text