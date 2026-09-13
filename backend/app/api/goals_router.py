"""
JARVIX Goals REST API Router.
Endpoints for CRUD operations on Goals and Milestones, backed by GoalRepository.
"""

import uuid
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models.base import HAS_SQLALCHEMY
from app.db.repositories.goal_repository import GoalRepository
from app.db.repositories.task_repository import TaskRepository

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

router = APIRouter(prefix="/api/goals", tags=["goals"])


class GoalCreateRequest(BaseModel):
    title: str
    category: str = "General"
    description: Optional[str] = None
    priority: str = "MEDIUM"
    deadline: Optional[str] = None
    available_time_per_day: Optional[int] = None


class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[str] = None


class MilestoneResponse(BaseModel):
    milestone_id: str
    goal_id: str
    title: str
    description: Optional[str] = None
    order_index: int = 0
    status: str = "ACTIVE"


class GoalResponse(BaseModel):
    goal_id: str
    user_id: str
    title: str
    category: str
    description: Optional[str] = None
    priority: str
    deadline: Optional[str] = None
    status: str
    available_time_per_day: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    milestones: List[MilestoneResponse] = []
    tasks_total: int = 0
    tasks_completed: int = 0


def _serialize_goal(goal, goal_repo, task_repo, user_id: str) -> dict:
    milestones_raw = goal_repo.list_milestones(goal.goal_id)
    milestones = [
        MilestoneResponse(
            milestone_id=m.milestone_id,
            goal_id=m.goal_id,
            title=m.title,
            description=getattr(m, "description", None),
            order_index=getattr(m, "order_index", 0),
            status=getattr(m, "status", "ACTIVE"),
        )
        for m in milestones_raw
    ]
    tasks = task_repo.list_tasks_for_goal(goal.goal_id, user_id)
    tasks_completed = sum(1 for t in tasks if getattr(t, "status", "") == "COMPLETED")

    return GoalResponse(
        goal_id=goal.goal_id,
        user_id=goal.user_id,
        title=goal.title,
        category=getattr(goal, "category", "General"),
        description=getattr(goal, "description", None),
        priority=getattr(goal, "priority", "MEDIUM"),
        deadline=str(goal.deadline) if getattr(goal, "deadline", None) else None,
        status=getattr(goal, "status", "ACTIVE"),
        available_time_per_day=getattr(goal, "available_time_per_day", None),
        created_at=str(goal.created_at) if getattr(goal, "created_at", None) else None,
        updated_at=str(goal.updated_at) if getattr(goal, "updated_at", None) else None,
        milestones=milestones,
        tasks_total=len(tasks),
        tasks_completed=tasks_completed,
    ).model_dump()


@router.get("", response_model=List[GoalResponse])
async def list_goals(
    user_id: str = Query(default="default_user"),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_session),
):
    goal_repo = GoalRepository(db)
    task_repo = TaskRepository(db)

    if status and status == "ACTIVE":
        goals = goal_repo.list_active_goals(user_id)
    else:
        goals = goal_repo.list_active_goals(user_id)
        if status:
            all_goals = db.query(
                __import__("app.db.models.goal", fromlist=["GoalModel"]).GoalModel
            ).filter_by(user_id=user_id).all()
            goals = [g for g in all_goals if getattr(g, "status", "") == status]

    return [_serialize_goal(g, goal_repo, task_repo, user_id) for g in goals]


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    request: GoalCreateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    goal_repo = GoalRepository(db)
    task_repo = TaskRepository(db)

    from app.db.repositories.user_repository import UserRepository
    UserRepository(db).get_or_create(user_id)

    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    goal = goal_repo.create_goal(
        goal_id=goal_id,
        user_id=user_id,
        title=request.title,
        category=request.category,
        description=request.description,
        priority=request.priority,
        available_time_per_day=request.available_time_per_day,
    )
    return _serialize_goal(goal, goal_repo, task_repo, user_id)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    goal_repo = GoalRepository(db)
    task_repo = TaskRepository(db)
    goal = goal_repo.get_goal(goal_id, user_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")
    return _serialize_goal(goal, goal_repo, task_repo, user_id)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    request: GoalUpdateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    goal_repo = GoalRepository(db)
    task_repo = TaskRepository(db)
    goal = goal_repo.get_goal(goal_id, user_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal '{goal_id}' not found.")

    if request.status:
        allowed = {"ACTIVE", "PAUSED", "COMPLETED", "ABANDONED"}
        if request.status not in allowed:
            raise HTTPException(status_code=422, detail=f"Invalid status '{request.status}'.")
        goal = goal_repo.update_goal_status(goal_id, user_id, request.status)
    if request.title is not None:
        goal.title = request.title
    if request.category is not None:
        goal.category = request.category
    if request.description is not None:
        goal.description = request.description
    if request.priority is not None:
        goal.priority = request.priority

    db.commit()
    db.refresh(goal)
    return _serialize_goal(goal, goal_repo, task_repo, user_id)
