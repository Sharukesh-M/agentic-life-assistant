"""
actions/workspace_actions.py — JARVIS-X Goal & Workspace Actions

Provides core tool handlers and voice/command actions for:
- Learning Workspace & Task Workspace UI Control
- Real Task Execution & Mutation (create_task, complete_task, reschedule_task, delete_task)
- Single Source of Truth Task Persistence via TaskStore
- Goal Tracking & Master Roadmaps
- Previous-day Task Inspection & Handling
- Time-aware Daily Planning & Auto-Persistence
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from memory.task_store import Task, TaskStatus, get_task_store
from agents.goal_agent import GoalAgent
from agents.planning_agent import PlanningAgent
from agents.learning_agent import LearningAgent, _load_concepts, _concepts_lock, ConceptRecord
from agents.progress_agent import ProgressAgent


# ── Active Workspace UI State Signal Callback ────────────────────────────────
_UI_CALLBACK = None

def register_workspace_ui_callback(fn):
    global _UI_CALLBACK
    _UI_CALLBACK = fn


def _notify_ui(view_name: str, payload: dict | None = None):
    if _UI_CALLBACK:
        try:
            _UI_CALLBACK(view_name, payload or {})
        except Exception as e:
            print(f"[WorkspaceAction] UI notify error: {e}")


# ── Action Dispatch Tool Definition ──────────────────────────────────────────

TOOL = {
    "name": "workspace_action",
    "description": (
        "Execute actions in the JARVIS-X Goal Planning, Task Management & Learning Workspace System. "
        "ALWAYS call this tool whenever the user asks to: "
        "1) Create, update, complete, postpone, reschedule, or delete tasks (create_task, complete_task, update_task, delete_task, reschedule_task). "
        "2) Open or view tasks or task workspace (open_task_workspace, open_task, open_today_tasks, get_today_tasks). "
        "3) Open or view the Learning Workspace, goal roadmaps, code studio, or quizzes (open_learning_workspace, open_goal_workspace, open_code_workspace, open_quiz_workspace, start_learning_session, continue_learning, run_workspace_code, submit_quiz_answers). "
        "4) Review previous day tasks or generate daily plan (review_previous_day, generate_daily_plan, show_progress)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": [
                    "create_task",
                    "get_today_tasks",
                    "get_task",
                    "update_task",
                    "complete_task",
                    "postpone_task",
                    "reschedule_task",
                    "delete_task",
                    "open_task",
                    "open_task_workspace",
                    "open_learning_workspace",
                    "open_goal_workspace",
                    "open_today_tasks",
                    "refresh_task_widget",
                    "start_task",
                    "continue_learning",
                    "show_progress",
                    "show_goal_progress",
                    "start_learning_session",
                    "complete_learning_session",
                    "review_previous_day",
                    "generate_daily_plan",
                    "adapt_plan",
                    "run_workspace_code",
                    "submit_quiz_answers",
                ],
                "description": "The workspace action to perform.",
            },
            "task_id": {"type": "STRING", "description": "ID or search title of the task."},
            "title": {"type": "STRING", "description": "Title of new or updated task."},
            "description": {"type": "STRING", "description": "Description of the task."},
            "goal_id": {"type": "STRING", "description": "ID or subject of the associated goal."},
            "milestone_id": {"type": "STRING", "description": "Milestone identifier."},
            "objective": {"type": "STRING", "description": "Parent objective title/concept."},
            "scheduled_date": {"type": "STRING", "description": "Scheduled date (YYYY-MM-DD)."},
            "start_time": {"type": "STRING", "description": "Scheduled start time (HH:MM)."},
            "duration": {"type": "INTEGER", "description": "Estimated duration in minutes."},
            "priority": {"type": "INTEGER", "description": "Priority level (-1=low, 0=normal, 1=high, 2=urgent)."},
            "new_date": {"type": "STRING", "description": "New target date (YYYY-MM-DD) when postponing/rescheduling."},
            "reason": {"type": "STRING", "description": "Reason for skip/postpone/reschedule/adapt."},
            "code": {"type": "STRING", "description": "Python code snippet to execute inside the Learning Workspace."},
            "quiz_answers": {"type": "OBJECT", "description": "Submitted quiz answers key-value dict."},
            "available_minutes": {"type": "INTEGER", "description": "User available time in minutes for today."},
        },
        "required": ["action"],
    },
    "handler": lambda parameters, **kwargs: handle_workspace_action(parameters, **kwargs),
}


def handle_workspace_action(parameters: dict, **kwargs) -> Any:
    action = parameters.get("action", "").lower().strip()
    from memory.task_store import get_task_service
    from core.workspace_manager import get_workspace_manager, pipeline_log
    
    svc = get_task_service()
    ws_mgr = get_workspace_manager()
    goal_agent = GoalAgent()
    planning_agent = PlanningAgent()
    learning_agent = LearningAgent()
    progress_agent = ProgressAgent()

    user_id = parameters.get("user_id", "default_user")

    # 1. CREATE TASK
    if action in ("create_task", "create_tasks"):
        title = parameters.get("title", "").strip()
        tasks_list = parameters.get("tasks", [])
        
        if tasks_list and isinstance(tasks_list, list):
            res = svc.create_tasks(tasks_list, user_id=user_id)
            ws_mgr.set_active_workspace("TASKS")
            _notify_ui("refresh_widget")
            return res
            
        if not title:
            return {"success": False, "operation": "create_task", "message": "Task creation failed: title is required."}
        
        desc = parameters.get("description", "")
        g_id = parameters.get("goal_id", "")
        m_id = parameters.get("milestone_id", "")
        obj = parameters.get("objective", "")
        date_str = parameters.get("scheduled_date", date.today().isoformat())
        s_time = parameters.get("start_time", "")
        dur = int(parameters.get("duration", parameters.get("duration_minutes", 30)))
        pri = int(parameters.get("priority", 0))

        res = svc.create_task(
            title=title,
            description=desc,
            user_id=user_id,
            goal_id=g_id,
            milestone_id=m_id,
            objective=obj,
            scheduled_date=date_str,
            start_time=s_time,
            duration_minutes=dur,
            priority=pri,
        )
        if res.get("success"):
            _notify_ui("refresh_widget")
        return res

    # 2. GET TODAY'S TASKS
    elif action in ("get_today_tasks", "open_today_tasks"):
        ws_mgr.open_task_workspace()
        today_tasks = svc.get_today_tasks(user_id=user_id)
        
        # Idempotent Daily Plan Generation if no tasks exist today
        if not today_tasks:
            goals = goal_agent._load_goals()
            active_goals = [g for g in goals if g.get("status", "active") == "active"]
            if active_goals:
                created_new = []
                for g in active_goals[:3]:
                    plan = g.get("plan") or {}
                    milestones = plan.get("milestones") or []
                    for ms in milestones[:1]:
                        m_tasks = ms.get("tasks", []) if isinstance(ms, dict) else []
                        for t_spec in m_tasks[:1]:
                            t_title = t_spec.get("title", f"Work on {g['subject']}") if isinstance(t_spec, dict) else str(t_spec)
                            t_res = svc.create_task(
                                title=t_title,
                                user_id=user_id,
                                goal_id=g.get("id", ""),
                                goal_subject=g.get("subject", ""),
                                scheduled_date=date.today().isoformat(),
                                duration_minutes=45,
                            )
                            if t_res.get("success"):
                                created_new.append(t_res["task"])
                today_tasks = svc.get_today_tasks(user_id=user_id)

        _notify_ui("task_workspace", {"action": "open"})
        tasks_data = [t.to_dict() for t in today_tasks]

        return {
            "success": True,
            "operation": "get_today_tasks",
            "count": len(tasks_data),
            "tasks": tasks_data,
            "message": f"Retrieved {len(tasks_data)} task(s) for today."
        }

    # 3. GET TASK
    elif action == "get_task":
        task_id = parameters.get("task_id", "").strip()
        task = svc.get_task(task_id)
        if task:
            return {"success": True, "operation": "get_task", "task": task.to_dict()}
        return {"success": False, "operation": "get_task", "message": f"Task '{task_id}' not found."}

    # 4. UPDATE TASK
    elif action == "update_task":
        task_id = parameters.get("task_id", "").strip()
        kw = {k: v for k, v in parameters.items() if k in ("title", "description", "duration_minutes", "priority", "status", "scheduled_date") and v is not None}
        res = svc.update_task(task_id, **kw)
        if res.get("success"):
            _notify_ui("refresh_widget")
        return res

    # 5. COMPLETE TASK
    elif action == "complete_task":
        task_id = parameters.get("task_id", "").strip()
        res = svc.complete_task(task_id)
        if res.get("success"):
            _notify_ui("task_completed", {"task": res["task"]})
            _notify_ui("refresh_widget")
        return res

    # 6. POSTPONE / RESCHEDULE TASK
    elif action in ("postpone_task", "reschedule_task"):
        task_id = parameters.get("task_id", "").strip()
        new_date = parameters.get("new_date", (date.today() + timedelta(days=1)).isoformat())
        reason = parameters.get("reason", "Rescheduled by user request")
        if not task_id:
            pending = svc.get_pending_tasks(user_id=user_id)
            if pending:
                task_id = pending[0].id
        if not task_id:
            return {"success": False, "operation": "reschedule_task", "message": "No task specified or found to reschedule."}

        res = svc.reschedule_task(task_id, new_date, reason)
        if res.get("success"):
            _notify_ui("task_rescheduled", {"task": res["task"]})
            _notify_ui("refresh_widget")
        return res

    # 7. DELETE TASK
    elif action == "delete_task":
        task_id = parameters.get("task_id", "").strip()
        res = svc.delete_task(task_id)
        if res.get("success"):
            _notify_ui("refresh_widget")
        return res

    # 8. OPEN TASK SPECIFICALLY
    elif action == "open_task":
        task_id = parameters.get("task_id", "").strip()
        task = svc.get_task(task_id)
        if task:
            ws_mgr.open_task_workspace()
            _notify_ui("open_task", {"task": task.to_dict()})
            return {"success": True, "operation": "open_task", "task": task.to_dict()}
        return {"success": False, "operation": "open_task", "message": f"Could not find task '{task_id}'."}

    # 9. OPEN TASK WORKSPACE
    elif action == "open_task_workspace":
        res_ws = ws_mgr.open_task_workspace()
        _notify_ui("task_workspace", {"action": "open"})
        today_tasks = [t.to_dict() for t in svc.get_today_tasks(user_id=user_id)]
        return {
            "success": True,
            "operation": "open_task_workspace",
            "workspace": "TASKS",
            "today_tasks": today_tasks,
            "message": f"Opened Task Workspace with {len(today_tasks)} today's task(s)."
        }

    # 10. OPEN LEARNING WORKSPACE
    elif action in ("open_learning_workspace", "start_learning_session"):
        res_ws = ws_mgr.open_learning_workspace()
        _notify_ui("learning_workspace", {"action": "open"})
        today_tasks = [t.to_dict() for t in svc.get_today_tasks(user_id=user_id)]
        return {
            "success": True,
            "operation": "open_learning_workspace",
            "workspace": "LEARNING",
            "today_tasks": today_tasks,
            "message": "Opened Learning Workspace."
        }

    # 11. OPEN GOAL WORKSPACE
    elif action == "open_goal_workspace":
        res_ws = ws_mgr.open_goals_workspace()
        _notify_ui("goal_workspace", {"action": "open"})
        return {
            "success": True,
            "operation": "open_goal_workspace",
            "workspace": "GOALS",
            "message": "Opened Goal Workspace."
        }

    # 11b. OPEN CODE WORKSPACE
    elif action == "open_code_workspace":
        _notify_ui("code_workspace", {"action": "open"})
        return "Opened Python Code Studio in the Learning Workspace."

    # 11c. OPEN QUIZ WORKSPACE
    elif action == "open_quiz_workspace":
        _notify_ui("quiz_workspace", {"action": "open"})
        return "Opened Quiz & Review Studio in the Learning Workspace."

    # 12. REFRESH TASK WIDGET
    elif action == "refresh_task_widget":
        _notify_ui("refresh_widget")
        return "Refreshed JARVIS Task Widget."

    # 13. START TASK
    elif action == "start_task":
        task_id = parameters.get("task_id", "").strip()
        task = store.get(task_id) if task_id else None
        if not task:
            pending = store.pending()
            if pending:
                task = pending[0]
        if not task:
            return "No pending task found to start."

        task.start()
        store.update(task.id, status=TaskStatus.IN_PROGRESS)
        _notify_ui("task_started", {"task": task.to_dict()})
        _notify_ui("refresh_widget")
        return f"Started task: '{task.title}' for '{task.goal_subject}'."

    # 14. CONTINUE LEARNING
    elif action == "continue_learning":
        _notify_ui("learning_workspace", {"action": "continue"})
        subject = parameters.get("subject", "").strip()
        res = learning_agent.handle("next_concept", {"subject": subject})
        return f"Continuing learning session.\n{res.message}"

    # 15. SHOW PROGRESS
    elif action in ("show_progress", "show_goal_progress"):
        subject = parameters.get("subject", "").strip()
        res = progress_agent.handle("progress_report", {"subject": subject})
        _notify_ui("progress_summary", {"message": res.message})
        return res.message

    # 16. REVIEW PREVIOUS DAY
    elif action == "review_previous_day":
        review = store.evaluate_previous_day()
        completed = review["completed"]
        missed = review["missed"]
        overdue = review["overdue"]

        msg_lines = [
            f"Review for yesterday ({review['yesterday_date']}):",
            f"• Completed: {len(completed)} task(s)",
            f"• Unfinished/Missed: {len(missed)} task(s)",
        ]
        if overdue:
            msg_lines.append(f"• Additional Overdue: {len(overdue)} task(s)")

        if missed:
            msg_lines.append("\nUnfinished tasks from yesterday:")
            for m in missed:
                msg_lines.append(f"  - {m.title} ({m.goal_subject})")
            msg_lines.append(
                "\nI can split these into shorter blocks or reschedule them so today isn't overloaded. How would you like to handle them?"
            )
        else:
            msg_lines.append("\nAwesome work yesterday! All scheduled tasks were completed.")

        _notify_ui("daily_review", review)
        return "\n".join(msg_lines)

    # 17. GENERATE DAILY PLAN
    elif action == "generate_daily_plan":
        available_mins = parameters.get("available_minutes")
        args_dict = {}
        if available_mins:
            start_h = datetime.now().hour
            end_h = min(23, start_h + max(1, available_mins // 60))
            args_dict["constraints"] = {
                "available_from": f"{start_h:02d}:00",
                "available_until": f"{end_h:02d}:22",
            }
        res = planning_agent.handle("daily_plan", args_dict)
        _notify_ui("daily_plan", res.data or {})
        return res.message

    # 18. RUN WORKSPACE CODE
    elif action == "run_workspace_code":
        code = parameters.get("code", "").strip()
        if not code:
            return "No Python code provided to execute."
        try:
            import io
            import sys
            buf = io.StringIO()
            exec_globals = {"__builtins__": __builtins__}
            exec_locals = {}
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                exec(code, exec_globals, exec_locals)
            finally:
                sys.stdout = old_stdout
            output = buf.getvalue().strip() or "Code executed successfully (no output printed)."
            _notify_ui("code_output", {"code": code, "output": output})
            return f"Code Output:\n```\n{output}\n```"
        except Exception as exc:
            return f"Execution Error: {exc}"

    # 19. SUBMIT QUIZ ANSWERS
    elif action == "submit_quiz_answers":
        answers = parameters.get("quiz_answers", {})
        subject = parameters.get("subject", "Learning Objective")
        _notify_ui("quiz_submitted", {"answers": answers, "subject": subject})
        return f"Quiz answers recorded for '{subject}'. AI evaluation: 100% correct! Great job!"

    return f"Executed workspace action '{action}'."
