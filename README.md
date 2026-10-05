# 🤖 JARVIS-X — Proactive Multi-Agent AI Life Assistant & Goal Planning System

JARVIS-X is a goal-aware, adaptive, multi-agent personal AI life assistant featuring real-time Multimodal Gemini Live WebSockets, PyQt6 Cyberpunk Desktop HUD, local HTTP Web Dashboard, Android companion phone bridge, single-source-of-truth task persistence, and an interactive Learning Studio.

---

## ✨ Key Features & Architecture

- **🎓 Interactive Learning & Code Studio**:
  - Visual learning components (`CONCEPT_CARD`, `INTERACTIVE_CODE`, `COMPARISON`, `PROCESS_FLOW`, `QUIZ`, `FLASHCARDS`).
  - Built-in Python code execution studio with real-time AI code review.
  - Adaptive concept mastery tracking stored in `memory/concepts.json`.

- **📋 Task & Goal Management System**:
  - Single Source of Truth `TaskStore` (`memory/tasks.json`) & `GoalAgent` (`memory/goals.json`).
  - Emergency daily plan auto-generation & auto-persistence for urgent deadlines.
  - Interactive Desktop HUD overlays & side task panel widget.

- **🎙️ Real-Time Voice & Multimodal Live Streaming**:
  - Gemini Live WebSocket integration (`models/gemini-2.0-flash-exp`).
  - Ultra-fast <50ms audio chunking & barge-in speech detection.
  - Native PyQt6 HUD with real-time voice state visualizers.

- **📱 Secure Android Phone Bridge Companion**:
  - Paired Android companion app (`jarvis-x-mobile`) over AES-256 WebSockets.
  - Call control, SMS/WhatsApp messaging, contact search, notification bridge, device status monitoring.

- **🖥️ Cross-Platform Local HTTP Dashboard**:
  - Fast, local web dashboard on port `8000` with zero external CDN dependencies.
  - Encrypted WebSockets with AES-256-CBC authentication.

---

## 🛠 Project Structure

```
.
├── main.py                         # Application entrypoint & Gemini Live event loop
├── ui.py                           # PyQt6 Cyberpunk HUD GUI & Overlay Windows
├── core/
│   ├── workspace_manager.py        # Central WorkspaceManager state & Event System
│   ├── learning_renderer.py        # Structured visual learning content builder
│   ├── state_manager.py            # Process-lifetime voice & app state singletons
│   ├── voice_controller.py         # Voice lifecycle state machine & barge-in handler
│   ├── orchestrator.py             # Agent intent router & fall-through dispatcher
│   ├── agent_bootstrap.py          # Agent registration engine
│   └── llm_client.py               # Local LLM fallback & Gemini API client
├── agents/                         # Dedicated Agent Modules
│   ├── goal_agent.py               # Master roadmaps & goal decomposition
│   ├── planning_agent.py           # Daily & weekly task schedule planner
│   ├── learning_agent.py           # Adaptive concept difficulty & teaching paths
│   ├── progress_agent.py           # Accomplishment & milestone analytics
│   ├── communication_agent.py      # Call screening, messaging & phone bridge
│   ├── memory_agent.py             # Context recall & fact manager
│   └── proactive_agent.py          # Proactive notifications & schedule monitor
├── actions/                        # Executable Tool Action Handlers
│   ├── workspace_actions.py        # Task CRUD, Learning Studio & Workspace actions
│   ├── open_app.py                 # Application launcher & workspace router
│   ├── phone_bridge.py             # Android device pairing & call control
│   ├── comm_actions.py              # Messaging & phone tools
│   ├── computer_control.py         # OS window automation & typing
│   ├── browser_control.py          # Web automation & tab controller
│   └── desktop.py                  # System controls & volume management
├── memory/                         # Single Source of Truth Databases
│   ├── tasks.json                  # TaskStore database
│   ├── goals.json                  # Goal tracking database
│   ├── concepts.json               # Learning concept mastery records
│   ├── profile.json                # User identity & background context
│   └── comm_data.json              # Paired devices & message logs
├── dashboard/                      # Web Dashboard Server
│   ├── server.py                   # FastAPI / Uvicorn HTTP server
│   └── static/app.html             # Responsive Web Dashboard UI
├── jarvis-x-mobile/                # Android Companion App (Kotlin / Jetpack Compose)
└── tests/                          # Integration Test Suite
    └── test_execution_pipeline.py  # End-to-end task & workspace pipeline tests
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Git**
- **Gemini API Key** (or Ollama for local LLM)

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Sharukesh-M/agentic-life-assistant.git
   cd agentic-life-assistant
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Keys**:
   Create or edit `config/api_keys.json`:
   ```json
   {
       "gemini_api_key": "YOUR_GEMINI_API_KEY",
       "os_system": "mac",
       "camera_index": 0
   }
   ```

---

## 💻 Usage

### Run Desktop HUD Application
```bash
python main.py
```

### Access Web Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🧪 Acceptance Test Commands

Try speaking or typing the following commands to JARVIS-X:

1. *"My placement exam is tomorrow. I need aptitude, Python, DSA, and logical reasoning. Go with the plan."*
2. *"Open my tasks."*
3. *"Open learning workspace."*
4. *"Teach me aptitude fundamentals."*
5. *"Run python code in code studio."*
6. *"What are my tasks today?"*
7. *"Mark task complete."*

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
