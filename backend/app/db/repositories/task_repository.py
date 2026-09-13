"""
Task Repository for Managing Task Persistence.
Enforces user isolation scoping and Completion-State Honesty.
"""

from typing import List, Optional, Any
from datetime import datetime
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.task import TaskModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_task(
        self,
        task_id: str,
        goal_id: str,
        user_id: str,
        title: str,
        milestone_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "MEDIUM",
        deadline: Optional[datetime] = None,
        estimated_minutes: int = 30,
        depends_on: Optional[str] = None
    ) -> TaskModel:
        task = TaskModel(
            task_id=task_id,
            goal_id=goal_id,
            milestone_id=milestone_id,
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            estimated_minutes=estimated_minutes,
            status="CREATED",
            depends_on=depends_on
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_task(self, task_id: str, user_id: str) -> Optional[TaskModel]:
        return self.session.query(TaskModel).filter(
            TaskModel.task_id == task_id,
            TaskModel.user_id == user_id
        ).first()

    def list_tasks_for_goal(self, goal_id: str, user_id: str) -> List[TaskModel]:
        return self.session.query(TaskModel).filter(
            TaskModel.goal_id == goal_id,
            TaskModel.user_id == user_id
        ).order_by(TaskModel.created_at.asc()).all()

    def list_user_tasks(self, user_id: str, status_filter: Optional[str] = None) -> List[TaskModel]:
        query = self.session.query(TaskModel).filter(TaskModel.user_id == user_id)
        if status_filter:
            query = query.filter(TaskModel.status == status_filter)
        return query.order_by(TaskModel.created_at.desc()).all()

    def update_task_status(
        self,
        task_id: str,
        user_id: str,
        new_status: str,
        source: Optional[str] = None
    ) -> TaskModel:
        """
        Updates task status with Completion-State Honesty enforcement.
        Rule: Task cannot be set to COMPLETED based on indirect signals (e.g. commit, login).
        Must originate from explicit user confirmation or verified signal source.
        """
        task = self.get_task(task_id, user_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found for user '{user_id}'")

        allowed_statuses = {"CREATED", "IN_PROGRESS", "COMPLETED", "SKIPPED", "POSTPONED", "RESCHEDULED"}
        if new_status not in allowed_statuses:
            raise ValueError(f"Invalid task status '{new_status}'")

        if new_status == "COMPLETED":
            indirect_signals = {"git_commit", "github_commit", "github_activity", "user_login", "indirect_mention", "automated_heuristic"}
            if source in indirect_signals or (source and "commit" in source.lower()):
                raise ValueError(
                    f"Honesty Rule Violation: Cannot set task COMPLETED from indirect signal '{source}'. "
                    f"Task state remains '{task.status}'. Requires explicit user confirmation."
                )

        task.status = new_status
        if source:
            task.completion_source = source
        self.session.commit()
        self.session.refresh(task)
        return task
