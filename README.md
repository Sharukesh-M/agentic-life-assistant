# JARVIX – Goal-Aware Proactive Agentic AI Life Assistant

JARVIX (also referred to as JARVIS-X) is a personalized, proactive, goal-oriented agentic AI life assistant — designed to decompose arbitrary user goals into milestones and tasks, track progress honestly, store tiered memory, run proactive checks, and interact via voice synthesis.

---

## 🏛️ Project Architecture

```text
JARVIX/
├── AGENTS.md                 # Primary directives & operational guidelines for AI coding agents
├── DESIGN.md                 # Visual design system, DTCG tokens, and WCAG accessibility standards
├── README.md                 # Project overview and quickstart guide
├── .gitignore                # Git exclusions
│
├── docs/                     # Documentation & specifications
│   ├── JARVIX_Prompt_Engineering_Specification.md   # Primary agent prompt architecture
│   └── JARVIX_Prompt_Engineering_Specification.txt  # Plaintext specification copy
│
├── .agents/                  # Agent Skills standard
│   └── skills/               # 23 modular task-specific skills (AntiSlop, UX/UI, A11y)
│
├── backend/                  # Python FastAPI application
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── agent/            # ReAct Orchestrator & agent routing
│   │   ├── memory/           # Tiered memory classifier (Working vs Long-Term)
│   │   ├── goals/            # Goal management & event correlation
│   │   ├── planning/         # Task decomposition agent
│   │   ├── rag/              # Grounded document retrieval
│   │   ├── tools/            # Tool execution wrappers
│   │   ├── mcp/              # Model Context Protocol integrations
│   │   ├── voice/            # Speech services (TTS Interface & OmniVoice implementation)
│   │   └── services/         # Proactive monitor & background jobs
│   ├── tests/
│   │   └── voice/            # Voice subsystem tests (test_omnivoice.py)
│   ├── requirements.txt      # Core backend dependencies
│   └── README.md             # Backend documentation
│
├── frontend/                 # Frontend application
│   └── README.md
│
├── tests/                    # Integration & end-to-end test suites
│   ├── integration/
│   └── e2e/
│
├── references/               # Supporting reference repositories (read-only)
│   ├── anti-slop/            # Anti-slop coding & UI rules
│   ├── awesome-design-md/    # Design system markdown specs library
│   ├── ux-ui-agent-skills/   # UX/UI skills framework
│   └── your-project/         # UX/UI sample application template
│
└── outputs/                  # Generated artifacts
    └── audio/                # Synthesized TTS WAV audio files
```

---

## 🚀 Quickstart Guide

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core dependencies
pip install -r requirements.txt

# Start backend server
python -m app.main
```

### Voice Subsystem Test

To verify OmniVoice TTS integration and hardware device auto-detection (`mps` / `cuda` / `cpu`):

```bash
# Run voice subsystem verification script
python -m backend.tests.voice.test_omnivoice
```

---

## 📄 Key Documentation

- [docs/JARVIX_Prompt_Engineering_Specification.md](file:///Users/sharukeshm/Desktop/1/docs/JARVIX_Prompt_Engineering_Specification.md): Complete prompt engineering specification, system personas, JSON schemas, and safety overlays.
- [AGENTS.md](file:///Users/sharukeshm/Desktop/1/AGENTS.md): Operational directives for AI agent workflows.
- [DESIGN.md](file:///Users/sharukeshm/Desktop/1/DESIGN.md): Design system tokens and accessibility guidelines.
