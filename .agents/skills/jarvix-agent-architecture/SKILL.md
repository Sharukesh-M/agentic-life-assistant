---
name: jarvix-agent-architecture
description: Instructions for developing, auditing, or extending the JARVIX multi-agent architecture (Orchestrator, Goal Manager, Planner, Memory Agent, Proactive Monitor). Use when modifying agent routing, capability layers, or multi-agent communication.
---

# JARVIX Multi-Agent Architecture Guide

This skill governs the development and extension of the multi-agent system architecture for **JARVIX – Goal-Aware Proactive Agentic AI Life Assistant**.

## 1. Core Architectural Topology

JARVIX uses a ReAct-style controller-specialist multi-agent topology:

```text
                        ┌────────────────────┐
                        │   Core System      │  (Persona, Priorities,
                        │   Prompt           │   Honesty, Style)
                        └─────────┬──────────┘
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
           ┌───────────┐  ┌───────────────┐  ┌────────────┐
           │  Memory   │  │ Orchestrator  │  │   Safety   │
           │  Agent    │◄─┤   Prompt      ├─►│ & Confirm. │
           └─────┬─────┘  └───────┬───────┘  └─────┬──────┘
                 │                │                │
      ┌──────────┼───────┬────────┼────────┬───────┼───────┐
      ▼          ▼       ▼        ▼        ▼       ▼       ▼
 ┌────────┐ ┌────────┐┌──────┐┌────────┐┌──────┐┌──────┐┌────────┐
 │  Goal  │ │Planning│ │Tool- ││Proact- ││Halluc││Error ││Response│
 │  Mgmt  │ │ Agent  │ │ Use  ││ive     ││-Prev ││Recov.││ Policy │
 └────────┘ └────────┘└──────┘└────────┘└──────┘└──────┘└────────┘
```

## 2. Agent Roles & Responsibilities

- **Orchestrator (`backend/app/agent/orchestrator.py`)**: Responsible for intent detection, capability routing, authorization checks, and confirmation gating.
- **Memory Agent (`backend/app/memory/`)**: Owns memory classification (`TEMPORARY_CONTEXT`, `LONG_TERM_PREFERENCE`, `IMPORTANT_INSTRUCTION`), retrieval filtering, and durable context storage.
- **Goal Management Agent (`backend/app/goals/`)**: Maintains goal registry, status tracking, multi-goal balancing, and event-goal semantic correlation.
- **Planning Agent (`backend/app/planning/`)**: Decomposes single goals into structured milestones and tasks, returning strict JSON (`status: plan` or `status: clarification_needed`).
- **Proactive Monitor (`backend/app/services/` & `backend/app/agent/`)**: Evaluates scheduled tool observations against active user goals and applies notification thresholds.
- **Voice Subsystem (`backend/app/voice/`)**: Decoupled TTS interface (`TTSInterface`) wrapping OmniVoice (`OmniVoiceTTS`).

## 3. Development Guidelines

1. **Strict Decoupling**: Specialist agents must never bypass the Orchestrator or directly mutate global state without validation.
2. **Schema Enforcement**: All intermediate agent responses must be parsed through Pydantic schemas in `backend/app/schemas/`.
3. **Standing Overlays**: Every agent turn inherits Hallucination Prevention, Safety & Confirmation, and Error Recovery overlays.
4. **Reference Spec**: Consult [docs/JARVIX_Prompt_Engineering_Specification.md](file:///Users/sharukeshm/Desktop/1/docs/JARVIX_Prompt_Engineering_Specification.md) for full system specifications.
