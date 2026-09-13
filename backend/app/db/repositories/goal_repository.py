"""
Goal Repository for Managing Goals and Milestones Persistence.
Enforces user isolation scoping (user_id).
"""

from typing import List, Optional, Any
from datetime import datetime
from app.db.models.base import HAS_SQLALCHEMY
from app.db.models.goal import GoalModel
from app.db.models.milestone import MilestoneModel

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

class GoalRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_goal(
        self,
        goal_id: str,
        user_id: str,
        title: str,
        category: str = "General",
        description: Optional[str] = None,
        priority: str = "MEDIUM",
        deadline: Optional[datetime] = None,
        available_time_per_day: Optional[int] = None
    ) -> GoalModel:
        goal = GoalModel(
            goal_id=goal_id,
            user_id=user_id,
            title=title,
            category=category,
            description=description,
            priority=priority,
            deadline=deadline,
            status="ACTIVE",
            available_time_per_day=available_time_per_day
        )
        self.session.add(goal)
        self.session.commit()
        self.session.refresh(goal)
        return goal

    def get_goal(self, goal_id: str, user_id: str) -> Optional[GoalModel]:
        return self.session.query(GoalModel).filter(
            GoalModel.goal_id == goal_id,
            GoalModel.user_id == user_id
        ).first()

    def list_active_goals(self, user_id: str) -> List[GoalModel]:
        return self.session.query(GoalModel).filter(
            GoalModel.user_id == user_id,
            GoalModel.status == "ACTIVE"
        ).order_by(GoalModel.created_at.desc()).all()

    def update_goal_status(self, goal_id: str, user_id: str, new_status: str) -> Optional[GoalModel]:
        goal = self.get_goal(goal_id, user_id)
        if goal:
            goal.status = new_status
            self.session.commit()
            self.session.refresh(goal)
        return goal

    def add_milestone(
        self,
        milestone_id: str,
        goal_id: str,
        title: str,
        description: Optional[str] = None,
        order_index: int = 0
    ) -> MilestoneModel:
        milestone = MilestoneModel(
            milestone_id=milestone_id,
            goal_id=goal_id,
            title=title,
            description=description,
            order_index=order_index,
            status="ACTIVE"
        )
        self.session.add(milestone)
        self.session.commit()
        self.session.refresh(milestone)
        return milestone

    def list_milestones(self, goal_id: str) -> List[MilestoneModel]:
        return self.session.query(MilestoneModel).filter(
            MilestoneModel.goal_id == goal_id
        ).order_by(MilestoneModel.order_index.asc()).all()
