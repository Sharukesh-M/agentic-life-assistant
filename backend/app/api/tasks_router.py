"""
JARVIX Tasks REST API Router.
Endpoints for CRUD operations on Tasks, backed by TaskRepository.
"""

import uuid
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models.base import HAS_SQLALCHEMY
from app.db.repositories.task_repository import TaskRepository

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    goal_id: str
    title: str
    milestone_id: Optional[str] = None
    description: Optional[str] = None
    priority: str = "MEDIUM"
    deadline: Optional[str] = None
    estimated_minutes: int = 30


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = "user_action"


class TaskResponse(BaseModel):
    task_id: str
    goal_id: str
    milestone_id: Optional[str] = None
    user_id: str
    title: str
    description: Optional[str] = None
    priority: str
    deadline: Optional[str] = None
    estimated_minutes: int
    status: str
    depends_on: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _serialize_task(task) -> dict:
    return TaskResponse(
        task_id=task.task_id,
        goal_id=task.goal_id,
        milestone_id=getattr(task, "milestone_id", None),
        user_id=task.user_id,
        title=task.title,
        description=getattr(task, "description", None),
        priority=getattr(task, "priority", "MEDIUM"),
        deadline=str(task.deadline) if getattr(task, "deadline", None) else None,
        estimated_minutes=getattr(task, "estimated_minutes", 30),
        status=getattr(task, "status", "CREATED"),
        depends_on=getattr(task, "depends_on", None),
        created_at=str(task.created_at) if getattr(task, "created_at", None) else None,
        updated_at=str(task.updated_at) if getattr(task, "updated_at", None) else None,
    ).model_dump()


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    user_id: str = Query(default="default_user"),
    status: Optional[str] = Query(default=None),
    goal_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_session),
):
    task_repo = TaskRepository(db)
    if goal_id:
        tasks = task_repo.list_tasks_for_goal(goal_id, user_id)
    else:
        tasks = task_repo.list_user_tasks(user_id, status_filter=status)
    return [_serialize_task(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    task_repo = TaskRepository(db)
    task = task_repo.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return _serialize_task(task)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    request: TaskCreateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    task_repo = TaskRepository(db)

    from app.db.repositories.user_repository import UserRepository
    UserRepository(db).get_or_create(user_id)

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    task = task_repo.create_task(
        task_id=task_id,
        goal_id=request.goal_id,
        user_id=user_id,
        title=request.title,
        milestone_id=request.milestone_id,
        description=request.description,
        priority=request.priority,
        estimated_minutes=request.estimated_minutes,
    )
    return _serialize_task(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    task_repo = TaskRepository(db)
    task = task_repo.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if request.status:
        try:
            task = task_repo.update_task_status(
                task_id, user_id, request.status,
                source=request.source or "user_action"
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    if request.title is not None:
        task.title = request.title
    if request.description is not None:
        task.description = request.description
    if request.priority is not None:
        task.priority = request.priority

    db.commit()
    db.refresh(task)
    return _serialize_task(task)
