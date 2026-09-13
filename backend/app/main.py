"""
JARVIX Backend FastAPI Main Entry Point.
Integrates Database Session management, Voice Subsystem, CRUD APIs, and Stateful Chat API.
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.db.models.base import HAS_SQLALCHEMY
if HAS_SQLALCHEMY:
    from sqlalchemy.orm import Session
else:
    Session = Any

from app.db.session import init_db, get_db_session
from app.voice.tts_router import router as tts_router
from app.agent.orchestrator import JARVIXOrchestrator
from app.agent.agent_context import AgentContext

from app.api.goals_router import router as goals_router
from app.api.tasks_router import router as tasks_router
from app.api.memory_router import router as memory_router
from app.api.notifications_router import router as notifications_router

app = FastAPI(
    title="JARVIX – Goal-Aware Proactive Agentic AI Life Assistant API",
    version="1.0.0",
    description="Backend API services for JARVIX multi-agent system including Database Persistence, Tiered Memory, Voice TTS, Agent Orchestrator, Planning, RAG, and MCP tools."
)

# CORS — development origins only; tighten for production
cors_origins = os.environ.get("JARVIX_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = JARVIXOrchestrator()

@app.on_event("startup")
def on_startup():
    """Initialize database tables on server startup."""
    try:
        init_db()
        print("[JARVIX DB] Database schema initialized successfully.")
    except Exception as e:
        print(f"[JARVIX DB Warning] DB init: {e}")

# Mount Routers
if tts_router:
    app.include_router(tts_router)
app.include_router(goals_router)
app.include_router(tasks_router)
app.include_router(memory_router)
app.include_router(notifications_router)

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    context_override: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    status: str
    intent: str
    required_capabilities: list
    result: Optional[Dict[str, Any]] = None
    confirmation_prompt: Optional[str] = None
    latency_seconds: float

@app.get("/health")
async def health_check():
    from app.db.session import get_active_backend
    backend_mode = get_active_backend()
    return {
        "status": "healthy",
        "service": "JARVIX Backend API",
        "version": "1.0.0",
        "database": "connected",
        "database_backend": backend_mode,
        "pgvector_enabled": (backend_mode == "POSTGRESQL")
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db_session)):
    """
    JARVIX End-to-End Stateful Chat API Endpoint.
    Routes user message through DB Memory/State Load -> Context -> Orchestrator -> LLM -> Validation -> DB Persistence -> Response.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message field cannot be empty.")

    context = AgentContext.load_from_db(user_id=request.user_id or "default_user", query=request.message, session=db)
    pipeline_result = orchestrator.execute_pipeline(request.message, context=context, db_session=db)

    return ChatResponse(
        status=pipeline_result.get("status", "completed"),
        intent=pipeline_result.get("intent", "general_conversation"),
        required_capabilities=pipeline_result.get("required_capabilities", []),
        result=pipeline_result.get("result"),
        confirmation_prompt=pipeline_result.get("confirmation_prompt"),
        latency_seconds=pipeline_result.get("latency_seconds", 0.0)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
