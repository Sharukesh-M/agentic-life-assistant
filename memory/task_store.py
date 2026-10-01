"""
memory/task_store.py - JARVIS-X Task Model & Storage

Phase 2 addition: A first-class Task data model that bridges the gap between
goals (long-term objects) and daily actionable work.

Data flows:
    GoalAgent creates goals (via goal_tracker plugin) -> goals.json
    PlanningAgent creates tasks (via TaskStore)       -> memory/tasks.json
    ProgressAgent reads tasks to detect patterns      -> ProgressReport
    ProactiveAgent reads tasks to surface pending work

No existing code is modified. goals.json remains unchanged.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Optional

import sys

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


TASKS_PATH = _get_base_dir() / "memory" / "tasks.json"
_lock = Lock()


# ---------------------------------------------------------------------------
# Task Status
# ---------------------------------------------------------------------------

class TaskStatus:
    PENDING   = "pending"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"

    ALL = (PENDING, COMPLETED, SKIPPED, POSTPONED, CANCELLED)


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """One concrete, time-bounded unit of work linked to a goal.

    Attributes:
        id                -- UUID hex (6 chars for readability)
        goal_id           -- References a goal in goals.json
        goal_subject      -- Denormalized for fast display (goal_subject)
        title             -- Concrete, actionable title (NOT "Study AI")
        description       -- Optional additional detail
        duration_minutes  -- Estimated work session length
        scheduled_date    -- ISO date string YYYY-MM-DD (optional)
        scheduled_time    -- HH:MM string (optional, for display)
        status            -- One of TaskStatus values
        completed_at      -- ISO datetime when completed (if status=completed)
        skip_count        -- How many times this specific task was skipped
        skip_reasons      -- Free-text notes from each skip
        created_at        -- ISO datetime of creation
        updated_at        -- ISO datetime of last status change
        priority          -- 0=normal, 1=high, -1=low
        tags              -- e.g. ["python", "coding", "morning"]
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    goal_id: str = ""
    goal_subject: str = ""
    title: str = ""
    description: str = ""
    duration_minutes: int = 30
    scheduled_date: Optional[str] = None     # "YYYY-MM-DD"
    scheduled_time: Optional[str] = None     # "HH:MM"
    status: str = TaskStatus.PENDING
    completed_at: Optional[str] = None
    skip_count: int = 0
    skip_reasons: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 0
    tags: list[str] = field(default_factory=list)

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def skip(self, reason: str = "") -> None:
        self.status = TaskStatus.SKIPPED
        self.skip_count += 1
        if reason:
            self.skip_reasons.append(reason)
        self.updated_at = datetime.now().isoformat()

    def postpone(self, new_date: Optional[str] = None) -> None:
        self.status = TaskStatus.POSTPONED
        if new_date:
            self.scheduled_date = new_date
        self.updated_at = datetime.now().isoformat()

    def reset_to_pending(self) -> None:
        self.status = TaskStatus.PENDING
        self.completed_at = None
        self.updated_at = datetime.now().isoformat()

    def is_overdue(self) -> bool:
        if not self.scheduled_date or self.status != TaskStatus.PENDING:
            return False
        try:
            return date.fromisoformat(self.scheduled_date) < date.today()
        except ValueError:
            return False

    def is_today(self) -> bool:
        if not self.scheduled_date:
            return False
        try:
            return date.fromisoformat(self.scheduled_date) == date.today()
        except ValueError:
            return False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        # Only pass fields that Task.__init__ recognizes
        known = {f.name for f in cls.__dataclass_fields__.values()}
        safe = {k: v for k, v in d.items() if k in known}
        return cls(**safe)

    def summary(self) -> str:
        parts = [self.title]
        if self.scheduled_date:
            parts.append(f"on {self.scheduled_date}")
        if self.scheduled_time:
            parts.append(f"at {self.scheduled_time}")
        parts.append(f"[{self.status}]")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# TaskStore
# ---------------------------------------------------------------------------

class TaskStore:
    """Persistent store for Task objects backed by memory/tasks.json.

    Thread-safe. All public methods hold _lock for the duration of the
    file read/modify/write cycle.
    """

    def __init__(self, path: Path = TASKS_PATH) -> None:
        self._path = path
        self._lock = Lock()

    # ── I/O ─────────────────────────────────────────────────────────────────

    def _load_raw(self) -> list[dict]:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
        except Exception as exc:
            print(f"[TaskStore] Load error: {exc}")
        return []

    def _save_raw(self, tasks: list[dict]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(tasks, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[TaskStore] Save error: {exc}")

    def _load(self) -> list[Task]:
        return [Task.from_dict(d) for d in self._load_raw()]

    def _save(self, tasks: list[Task]) -> None:
        self._save_raw([t.to_dict() for t in tasks])

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(self, task: Task) -> Task:
        """Persist a new task. Returns the saved task."""
        with self._lock:
            tasks = self._load()
            tasks.append(task)
            self._save(tasks)
        return task

    def create_many(self, new_tasks: list[Task]) -> list[Task]:
        """Batch create. More efficient than calling create() in a loop."""
        with self._lock:
            tasks = self._load()
            tasks.extend(new_tasks)
            self._save(tasks)
        return new_tasks

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            for task in self._load():
                if task.id == task_id:
                    return task
        return None

    def update(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update fields on a task by ID. Returns updated task or None."""
        with self._lock:
            tasks = self._load()
            target = None
            for task in tasks:
                if task.id == task_id:
                    for key, val in kwargs.items():
                        if hasattr(task, key):
                            setattr(task, key, val)
                    task.updated_at = datetime.now().isoformat()
                    target = task
                    break
            if target:
                self._save(tasks)
            return target

    def delete(self, task_id: str) -> bool:
        """Remove a task permanently. Returns True if found and deleted."""
        with self._lock:
            tasks = self._load()
            before = len(tasks)
            tasks = [t for t in tasks if t.id != task_id]
            if len(tasks) < before:
                self._save(tasks)
                return True
            return False

    # ── Queries ─────────────────────────────────────────────────────────────

    def all(self) -> list[Task]:
        with self._lock:
            return self._load()

    def for_goal(self, goal_id: str) -> list[Task]:
        with self._lock:
            return [t for t in self._load() if t.goal_id == goal_id]

    def for_date(self, iso_date: str) -> list[Task]:
        with self._lock:
            return [t for t in self._load() if t.scheduled_date == iso_date]

    def today(self) -> list[Task]:
        return self.for_date(date.today().isoformat())

    def pending(self, goal_id: Optional[str] = None) -> list[Task]:
        with self._lock:
            tasks = [t for t in self._load() if t.status == TaskStatus.PENDING]
            if goal_id:
                tasks = [t for t in tasks if t.goal_id == goal_id]
            return tasks

    def completed(self, goal_id: Optional[str] = None) -> list[Task]:
        with self._lock:
            tasks = [t for t in self._load() if t.status == TaskStatus.COMPLETED]
            if goal_id:
                tasks = [t for t in tasks if t.goal_id == goal_id]
            return tasks

    def skipped(self, goal_id: Optional[str] = None) -> list[Task]:
        with self._lock:
            tasks = [t for t in self._load() if t.status == TaskStatus.SKIPPED]
            if goal_id:
                tasks = [t for t in tasks if t.goal_id == goal_id]
            return tasks

    def overdue(self) -> list[Task]:
        with self._lock:
            return [t for t in self._load() if t.is_overdue()]

    def search(self, keyword: str) -> list[Task]:
        kw = keyword.lower()
        with self._lock:
            return [
                t for t in self._load()
                if kw in t.title.lower()
                or kw in t.description.lower()
                or kw in t.goal_subject.lower()
            ]

    # ── Statistics ───────────────────────────────────────────────────────────

    def goal_stats(self, goal_id: str) -> dict:
        """Return completion statistics for a goal."""
        tasks = self.for_goal(goal_id)
        total = len(tasks)
        if total == 0:
            return {
                "total": 0, "completed": 0, "skipped": 0,
                "pending": 0, "completion_rate": 0.0,
            }
        by_status = {s: 0 for s in TaskStatus.ALL}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
        completed = by_status[TaskStatus.COMPLETED]
        done = completed + by_status[TaskStatus.SKIPPED]
        return {
            "total":           total,
            "completed":       completed,
            "skipped":         by_status[TaskStatus.SKIPPED],
            "pending":         by_status[TaskStatus.PENDING],
            "postponed":       by_status[TaskStatus.POSTPONED],
            "completion_rate": round(completed / done, 2) if done > 0 else 0.0,
        }

    def skip_pattern(self, goal_id: str, window_days: int = 7) -> dict:
        """Detect recurring skip patterns for a goal within window_days.

        Returns:
            {
                "has_pattern": bool,
                "consecutive_skips": int,
                "most_skipped_time": str | None,  # HH:MM slot if identifiable
                "suggestion": str,
            }
        """
        tasks = self.for_goal(goal_id)
        recent = []
        cutoff = datetime.now().timestamp() - (window_days * 86400)
        for t in tasks:
            try:
                ts = datetime.fromisoformat(t.created_at).timestamp()
                if ts >= cutoff:
                    recent.append(t)
            except Exception:
                pass

        skipped = [t for t in recent if t.status == TaskStatus.SKIPPED]
        consecutive = len(skipped)

        # Count time slot frequency for skips
        time_counts: dict[str, int] = {}
        for t in skipped:
            slot = t.scheduled_time or "unknown"
            time_counts[slot] = time_counts.get(slot, 0) + 1

        most_skipped_time = None
        if time_counts:
            most_skipped_time = max(time_counts, key=lambda k: time_counts[k])

        has_pattern = consecutive >= 3
        suggestion = ""
        if has_pattern:
            if most_skipped_time and most_skipped_time != "unknown":
                suggestion = (
                    f"Tasks at {most_skipped_time} have been skipped "
                    f"{consecutive} time(s). Consider a different time slot."
                )
            else:
                suggestion = (
                    f"{consecutive} tasks skipped recently. "
                    "Consider shorter sessions or a schedule adjustment."
                )

        return {
            "has_pattern":        has_pattern,
            "consecutive_skips":  consecutive,
            "most_skipped_time":  most_skipped_time,
            "suggestion":         suggestion,
        }


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------

_default_store: Optional[TaskStore] = None
_store_lock = Lock()


def get_task_store() -> TaskStore:
    """Return the process-level TaskStore singleton."""
    global _default_store
    if _default_store is None:
        with _store_lock:
            if _default_store is None:
                _default_store = TaskStore()
    return _default_store
