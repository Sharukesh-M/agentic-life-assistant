---
name: jarvix-memory-system
description: Guidelines for implementing and validating JARVIX OS-inspired tiered memory system (working context vs durable storage). Use when building or debugging memory classification, retrieval, or storage policies.
---

# JARVIX Tiered Memory System Guide

This skill governs the development and validation of the OS-inspired tiered memory architecture in `backend/app/memory/`.

## 1. Classification Categories

Every incoming piece of information evaluated by the Memory Agent must be classified into exactly one category:

- `TEMPORARY_CONTEXT`: Relevant only to current active turn/session. Do NOT persist.
- `LONG_TERM_PREFERENCE`: Durable trait or learning preference (e.g. "prefers worked examples").
- `GOAL / TASK`: Structured goal object owned by Goal Management, not raw text memory.
- `IMPORTANT_INSTRUCTION`: Explicit standing user constraint (e.g. "always ask before scheduling after 6pm").
- `IRRELEVANT`: Discard immediately.

## 2. Storage Rules & Safety Constraints

- Store **only** `LONG_TERM_PREFERENCE` and `IMPORTANT_INSTRUCTION` items.
- **Sensitive Information Barrier**: Never store financial credentials, health details, government IDs, or protected personal attributes without explicit consent and storage policy authorization.
- Use durable phrasing over volatile dates (e.g. "prefers evening sessions" rather than a specific date).

## 3. Retrieval Protocol

- Perform semantic retrieval filtered to the active user query.
- Never dump full memory stores into LLM context budget.
- If retrieval returns empty, return `no_relevant_memory: true` — never hallucinate memories.
