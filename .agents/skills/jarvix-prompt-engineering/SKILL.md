---
name: jarvix-prompt-engineering
description: Rules and guidelines for creating, modifying, and assembling JARVIX runtime prompts and standing overlays. Use when editing backend runtime prompt files or loader logic.
---

# JARVIX Prompt Engineering Development Guide

This skill governs the structure, composition, and maintenance of runtime prompts in `backend/app/prompts/`.

## 1. Instruction Priority Hierarchy

Every runtime prompt loaded by JARVIX must respect the 5-level instruction priority hierarchy:

1. **Safety and Honesty Constraints** (Never violated under any condition)
2. **Explicit Current-Turn User Instruction**
3. **Active Goal Constraints and Deadlines**
4. **Stored User Preferences**
5. **General Helpfulness Heuristics**

## 2. Directory Structure (`backend/app/prompts/`)

```text
backend/app/prompts/
├── core/
│   └── system.md               # Base persona & core principles
├── memory/
│   └── memory_agent.md         # Memory classification & retrieval rules
├── goals/
│   └── goal_management.md      # Goal record fields & correlation scoring
├── planning/
│   └── planning_agent.md       # Task decomposition & JSON contract
├── orchestration/
│   └── orchestrator.md         # ReAct decision loop & routing contract
├── proactive/
│   └── proactive_monitor.md    # Fresh observations & notification gates
├── tool_use/
│   └── tool_use.md             # Tool necessity & verification steps
├── overlays/
│   ├── hallucination_prevention.md
│   ├── safety_confirmation.md
│   └── error_recovery.md
└── response/
    └── response_policy.md      # User-facing response formatting
```

## 3. Standing Overlays

All prompts inherit three standing overlays injected dynamically by `backend/app/agent/prompt_loader.py`:
- **Hallucination Prevention**: Never fabricate facts, tool calls, or completed actions.
- **Safety & Confirmation**: Run the Reversibility Test before executing high-impact actions.
- **Error Recovery**: State failures plainly in plain language; offer next step; log details.

## 4. Design Guidelines for Runtime Prompts

- **No Prose Surrounding JSON**: Structured JSON prompts must explicitly state `Output ONLY valid JSON, no markdown code block fences, no surrounding prose`.
- **Explicit Input Blocks**: Standardize context interpolation with labeled tags (`SYSTEM:`, `USER_CONTEXT:`, `GOAL_STATE:`, `TOOL_RESULTS:`).
- **Uncertainty Phrasing**: Standardize "I don't have a reliable way to verify that right now" for missing data.
