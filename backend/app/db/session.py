"""
Database Session and Engine Management.
Supports PostgreSQL / SQLite via SQLAlchemy when installed, with InMemory fallback when SQLAlchemy is not installed.
"""

from typing import Generator, Optional, Any, List, Dict

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    from app.db.config import DBConfig
    from app.db.models.base import Base
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    Base = None
    Session = Any
    from app.db.config import DBConfig

_engine = None
_SessionFactory = None

class InMemoryStore:
    """In-memory data store fallback when SQLAlchemy is not installed."""
    def __init__(self):
        self.users: Dict[str, Any] = {}
        self.goals: Dict[str, Any] = {}
        self.milestones: Dict[str, Any] = {}
        self.tasks: Dict[str, Any] = {}
        self.memories: Dict[str, Any] = {}
        self.agent_runs: Dict[str, Any] = {}
        self.notifications: Dict[str, Any] = {}

class InMemoryQuery:
    def __init__(self, data_list: List[Any]):
        self._data = list(data_list)

    def filter(self, *criterion) -> 'InMemoryQuery':
        filtered = []
        for item in self._data:
            match = True
            for crit in criterion:
                if isinstance(crit, tuple) and len(crit) == 3:
                    op, attr, val = crit
                    item_val = getattr(item, attr, None)
                    if op == "eq" and item_val != val:
                        match = False
                        break
                    elif op == "ne" and item_val == val:
                        match = False
                        break
            if match:
                filtered.append(item)
        return InMemoryQuery(filtered)

    def filter_by(self, **kwargs) -> 'InMemoryQuery':
        filtered = []
        for item in self._data:
            match = True
            for k, v in kwargs.items():
                if getattr(item, k, None) != v:
                    match = False
                    break
            if match:
                filtered.append(item)
        return InMemoryQuery(filtered)

    def order_by(self, *args) -> 'InMemoryQuery':
        data = list(self._data)
        for arg in reversed(args):
            if isinstance(arg, tuple) and len(arg) == 2:
                direction, attr = arg
                reverse = (direction == "desc")
                data.sort(key=lambda x: getattr(x, attr, None) or "", reverse=reverse)
        return InMemoryQuery(data)

    def limit(self, n: int) -> 'InMemoryQuery':
        return InMemoryQuery(self._data[:n])

    def first(self) -> Optional[Any]:
        return self._data[0] if self._data else None

    def all(self) -> List[Any]:
        return list(self._data)

class InMemorySession:
    """In-memory Session mock providing transaction interface."""
    store = InMemoryStore()

    def __init__(self):
        self._added: List[Any] = []

    def add(self, instance: Any):
        self._added.append(instance)

    def commit(self):
        for inst in self._added:
            model_name = inst.__class__.__name__
            if "User" in model_name:
                self.store.users[getattr(inst, "user_id")] = inst
            elif "Goal" in model_name:
                self.store.goals[getattr(inst, "goal_id")] = inst
            elif "Milestone" in model_name:
                self.store.milestones[getattr(inst, "milestone_id")] = inst
            elif "Task" in model_name:
                self.store.tasks[getattr(inst, "task_id")] = inst
            elif "Memory" in model_name:
                self.store.memories[getattr(inst, "memory_id")] = inst
            elif "AgentRun" in model_name:
                self.store.agent_runs[getattr(inst, "run_id")] = inst
            elif "Notification" in model_name:
                self.store.notifications[getattr(inst, "notification_id")] = inst
        self._added.clear()

    def rollback(self):
        self._added.clear()

    def refresh(self, instance: Any):
        pass

    def close(self):
        pass

    def query(self, model_cls: Any) -> InMemoryQuery:
        model_name = model_cls.__name__
        if "User" in model_name:
            items = list(self.store.users.values())
        elif "Goal" in model_name:
            items = list(self.store.goals.values())
        elif "Milestone" in model_name:
            items = list(self.store.milestones.values())
        elif "Task" in model_name:
            items = list(self.store.tasks.values())
        elif "Memory" in model_name:
            items = list(self.store.memories.values())
        elif "AgentRun" in model_name:
            items = list(self.store.agent_runs.values())
        elif "Notification" in model_name:
            items = list(self.store.notifications.values())
        else:
            items = []
        return InMemoryQuery(items)

def get_engine(config: Optional[DBConfig] = None):
    global _engine
    if not HAS_SQLALCHEMY:
        return None

    if _engine is not None:
        return _engine

    if config is None:
        config = DBConfig.from_env()

    url = config.database_url
    connect_args = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        _engine = create_engine(url, echo=config.echo_sql, connect_args=connect_args)
    else:
        _engine = create_engine(
            url,
            echo=config.echo_sql,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow
        )
    return _engine

def get_session_factory(config: Optional[DBConfig] = None):
    global _SessionFactory
    if not HAS_SQLALCHEMY:
        return InMemorySession

    if _SessionFactory is not None:
        return _SessionFactory

    engine = get_engine(config)
    _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory

def get_active_backend(config: Optional[DBConfig] = None) -> str:
    """Explicitly returns the active database engine mode (POSTGRESQL, SQLITE, or IN_MEMORY)."""
    if config is None:
        config = DBConfig.from_env()
    return config.get_active_backend()

def init_db(config: Optional[DBConfig] = None):
    """
    Initializes database schema tables and logs active backend mode explicitly.
    """
    if config is None:
        config = DBConfig.from_env()
    backend_mode = config.get_active_backend()
    print(f"[JARVIX DB Backend] Initializing Database (Mode: {backend_mode}, URL: {config.database_url})")

    if not HAS_SQLALCHEMY:
        InMemorySession.store = InMemoryStore()
        return

    engine = get_engine(config)
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Any, None, None]:
    """
    FastAPI dependency yielding a transactional DB session.
    """
    if not HAS_SQLALCHEMY:
        session = InMemorySession()
        try:
            yield session
        finally:
            session.close()
        return

    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
