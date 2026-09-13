# JARVIX Backend System

Backend service architecture for **JARVIX – Goal-Aware Proactive Agentic AI Life Assistant**.

## Architecture Overview

```text
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── agent/               # ReAct Orchestrator & agent context loading
│   ├── db/                  # Persistent Database & Memory Layer
│   │   ├── config.py        # Database URL & connection pool configuration
│   │   ├── session.py       # Engine, Session management, & backend mode reporter
│   │   ├── memory_service.py # High-level Memory Service API
│   │   ├── models/          # User, Goal, Task, Memory, Run, & Notification entities
│   │   ├── repositories/    # Data Access Repositories with safety & honesty gates
│   │   └── migrations/      # Alembic migration scripts (001_initial_schema.py)
│   ├── llm/                 # LLM Provider Abstraction Layer
│   ├── prompts/             # System Prompts & Standing Safety Overlays
│   ├── schemas/             # Pydantic JSON Schemas for Agent Planning
│   └── voice/               # Voice Subsystem & OmniVoice TTS
│
├── tests/
│   ├── integration/         # PostgreSQL, Memory & Cross-Process Persistence Integration Tests
│   └── test_*.py            # Unit & Pipeline Test Suites
│
├── requirements.txt         # Core dependencies
└── README.md                # System documentation
```

## Running Backend & Database Setup

### 1. Database Configuration
Set environment variable `DATABASE_URL` in `.env`:

```bash
# PostgreSQL Production / Local Dev setup:
DATABASE_URL=postgresql://jarvix_user:jarvix_password@localhost:5432/jarvix_db

# SQLite Local Development / Offline test setup:
DATABASE_URL=sqlite:///./jarvix.db
```

### 2. Alembic Schema Migrations
Initialize database tables using Alembic:

```bash
cd backend/app/db/migrations
alembic upgrade head
```

### 3. Database Engine Backend Transparency
JARVIX explicitly reports its active database backend on startup and `/health` API check:
* `POSTGRESQL`: Active when PostgreSQL URL is configured and SQLAlchemy + psycopg2 + pgvector are installed.
* `SQLITE`: Active when SQLite URL is configured with SQLAlchemy.
* `IN_MEMORY`: Fallback mode for isolated sandbox test environments.

### 4. Running Backend API Server

```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python -m app.main
```

## Running Test Suite

```bash
# Run all unit and integration test suites
python -m unittest discover -s backend/tests -p "test_*.py"

# Run database performance benchmark
python -m unittest backend/tests/integration/test_performance.py
```

