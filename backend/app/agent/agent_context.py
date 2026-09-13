"""
Agent Context Data Container for JARVIX Execution.
Supports loading persistent state from Database (User, Goals, Tasks, Memories).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AgentContext:
    user_id: str = "default_user"
    user_profile: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    active_goals: List[Dict[str, Any]] = field(default_factory=list)
    existing_tasks: List[Dict[str, Any]] = field(default_factory=list)
    working_memory: List[str] = field(default_factory=list)
    retrieved_memories: List[str] = field(default_factory=list)
    tool_observations: Dict[str, Any] = field(default_factory=dict)
    quiet_hours: bool = False

    @classmethod
    def load_from_db(cls, user_id: str, query: str = "", session: Optional[Any] = None) -> 'AgentContext':
        """
        Loads bounded user context from database (active goals, relevant tasks, memories).
        """
        if session is None:
            return cls(user_id=user_id)

        try:
            from app.db.repositories.goal_repository import GoalRepository
            from app.db.repositories.task_repository import TaskRepository
            from app.db.memory_service import MemoryService

            goal_repo = GoalRepository(session)
            task_repo = TaskRepository(session)
            memory_service = MemoryService(session)

            # 1. Retrieve Active Goals
            goals_db = goal_repo.list_active_goals(user_id)
            active_goals = [
                {
                    "goal_id": g.goal_id,
                    "title": g.title,
                    "category": g.category,
                    "priority": g.priority
                }
                for g in goals_db
            ]

            # 2. Retrieve Active Tasks
            tasks_db = task_repo.list_user_tasks(user_id)
            existing_tasks = [
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority
                }
                for t in tasks_db
            ]

            # 3. Retrieve Relevant Memories
            memories_db = memory_service.retrieve_memories(user_id, query=query, limit=5)
            retrieved_memories = [m.content for m in memories_db]

            return cls(
                user_id=user_id,
                active_goals=active_goals,
                existing_tasks=existing_tasks,
                retrieved_memories=retrieved_memories
            )
        except Exception as e:
            # Fallback cleanly if DB session fails
            return cls(user_id=user_id)
