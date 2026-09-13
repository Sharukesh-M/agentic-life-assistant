"""
JARVIX Memory REST API Router.
Exposes user-manageable preferences and instructions only. Internal memory records remain hidden.
"""

import uuid
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models.base import HAS_SQLALCHEMY
from app.db.repositories.memory_repository import MemoryRepository, SensitiveDataViolation

if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryCreateRequest(BaseModel):
    classification: str = "LONG_TERM_PREFERENCE"
    content: str


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    importance: Optional[float] = None


class MemoryResponse(BaseModel):
    memory_id: str
    classification: str
    content: str
    importance: float
    source: str
    created_at: Optional[str] = None


def _serialize_memory(mem) -> dict:
    return MemoryResponse(
        memory_id=mem.memory_id,
        classification=getattr(mem, "classification", ""),
        content=mem.content,
        importance=getattr(mem, "importance", 1.0),
        source=getattr(mem, "source", "user_interaction"),
        created_at=str(mem.created_at) if getattr(mem, "created_at", None) else None,
    ).model_dump()


@router.get("/preferences", response_model=List[MemoryResponse])
async def list_preferences(
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    """Returns active long-term preferences and instructions. Does not expose internal records."""
    mem_repo = MemoryRepository(db)
    records = mem_repo.list_active_memories(user_id)
    return [_serialize_memory(r) for r in records]


@router.post("/preferences", response_model=MemoryResponse, status_code=201)
async def create_preference(
    request: MemoryCreateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    mem_repo = MemoryRepository(db)
    from app.db.repositories.user_repository import UserRepository
    UserRepository(db).get_or_create(user_id)

    memory_id = f"mem_{uuid.uuid4().hex[:12]}"
    try:
        record = mem_repo.store_memory(
            memory_id=memory_id,
            user_id=user_id,
            classification=request.classification,
            content=request.content,
            source="user_action",
        )
    except SensitiveDataViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize_memory(record)


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_preference(
    memory_id: str,
    request: MemoryUpdateRequest,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    mem_repo = MemoryRepository(db)
    records = mem_repo.list_active_memories(user_id)
    target = next((r for r in records if r.memory_id == memory_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")

    if request.content is not None:
        try:
            mem_repo.inspect_sensitive_data(request.content)
        except SensitiveDataViolation as e:
            raise HTTPException(status_code=422, detail=str(e))
        target.content = request.content.strip()
    if request.importance is not None:
        target.importance = request.importance

    db.commit()
    db.refresh(target)
    return _serialize_memory(target)


@router.delete("/{memory_id}", status_code=204)
async def delete_preference(
    memory_id: str,
    user_id: str = Query(default="default_user"),
    db: Session = Depends(get_db_session),
):
    mem_repo = MemoryRepository(db)
    records = mem_repo.list_active_memories(user_id)
    target = next((r for r in records if r.memory_id == memory_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_id}' not found.")

    target.is_active = False
    db.commit()
    return None
