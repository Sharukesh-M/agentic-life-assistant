---
name: memory
description: Store, retrieve, and manage persistent user facts across sessions
purpose: Maintain continuity across conversations without fabricating or losing important context
triggers:
  - memory_agent
  - save_memory
  - recall_memory
  - memory
---

## Memory Skill

Memory provides continuity. It must be honest, relevant, and never fabricated.

## What to Persist

Persist (via save_memory):
- Name, language, city, role, age
- Active goals and their context
- User preferences (style, tone, schedule)
- Recurring constraints (work hours, commitments)
- Important decisions made
- Projects being worked on

Do NOT persist:
- Every conversational exchange
- One-time commands (open app, search, etc.)
- Weather results, news, transient facts

## Memory Categories

| Category | Examples |
|---|---|
| identity | name, age, language, nationality, role |
| goals | active goal subjects, target dates |
| preferences | preferred study time, learning style, language |
| constraints | work schedule, existing commitments |
| projects | JARVIS-X, research paper, startup |
| progress | concept mastery, completion patterns |
| decisions | architecture choices, priority decisions |
| notes | anything else worth remembering |

## Retrieval

Before saying "I don't know" about something personal:
1. Check if it's in the current system prompt memory block
2. If it appears under [ALSO REMEMBERED], call `recall_memory` first
3. Only say "I don't remember" if recall_memory also returns nothing

## Memory Lifecycle

- New explicit information **overrides** outdated information
- Never fabricate memory to seem knowledgeable
- If memory is unavailable, continue with current context — do not pretend
- Session summaries are saved at session end via `_save_session_summary`

## Structured Goal Memory

Goals are NOT stored in long_term.json — they live in memory/goals.json.
Access goals via `goal_tracker` plugin, not via save_memory.
