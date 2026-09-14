"""
todo_list.py — simple task manager for JARVIS
Drop into plugins/. Stores tasks in memory/todos.json.
"""

import json
import uuid
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "memory" / "todos.json"

PLUGIN = {
    "name": "todo_list",
    "description": (
        "Add, list, complete, or remove items on a simple to-do list. "
        "Trigger phrases: 'add a task...', 'what's on my to-do list', "
        "'mark ... as done', 'remove ... from my list'. Do NOT use "
        "calendar_plugin here — calendar is for dated events, this tool "
        "is for a plain undated task list."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["add", "list", "complete", "remove"],
                "description": "add a task, list open tasks, mark one done, or remove one.",
            },
            "task": {"type": "STRING", "description": "Task description (required for 'add')."},
            "task_id": {"type": "STRING", "description": "Task ID (required for 'complete' and 'remove')."},
        },
        "required": ["action"],
    },
}


def _load():
    if not DATA_PATH.exists():
        return []
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _save(tasks):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def _add(task):
    tasks = _load()
    item = {"id": uuid.uuid4().hex[:6], "task": task, "done": False}
    tasks.append(item)
    _save(tasks)
    return f"Added to your list: '{task}'. ID: {item['id']}."


def _list():
    tasks = [t for t in _load() if not t["done"]]
    if not tasks:
        return "Your to-do list is empty."
    lines = [f"{t['task']} (id: {t['id']})" for t in tasks]
    return f"You have {len(tasks)} open task(s): " + "; ".join(lines)


def _complete(task_id):
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            _save(tasks)
            return f"Marked '{t['task']}' as done."
    return f"No task found with id {task_id}."


def _remove(task_id):
    tasks = _load()
    remaining = [t for t in tasks if t["id"] != task_id]
    if len(remaining) == len(tasks):
        return f"No task found with id {task_id}."
    _save(remaining)
    return f"Removed task {task_id}."


def run(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "")
    task = parameters.get("task")
    task_id = parameters.get("task_id")

    try:
        if action == "add":
            result_text = "What's the task?" if not task else _add(task)
        elif action == "list":
            result_text = _list()
        elif action == "complete":
            result_text = "Which task id is done?" if not task_id else _complete(task_id)
        elif action == "remove":
            result_text = "Which task id should I remove?" if not task_id else _remove(task_id)
        else:
            result_text = f"Sir, I don't recognize the to-do action '{action}'."
    except Exception as e:
        return f"Sir, todo_list plugin failed: {e}"

    if player:
        try:
            player.write_log(f"JARVIS: {result_text}")
        except Exception:
            pass
    return result_text