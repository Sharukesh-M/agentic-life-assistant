---
name: jarvix-goal-planning
description: Guidelines for goal onboarding, milestone/task decomposition, multi-goal balancing, and structured plan output schemas. Use when building or debugging goal management or planning features.
---

# JARVIX Goal Management & Planning Guide

This skill governs goal onboarding, multi-goal balancing, milestone decomposition, and structured output parsing in `backend/app/goals/` and `backend/app/planning/`.

## 1. Goal Record Fields

Structured Goal schema fields:
`goal_id`, `title`, `category` (free-text, never hardcoded), `description`, `priority` (`HIGH`/`MEDIUM`/`LOW`), `deadline` (nullable ISO date), `status` (`ACTIVE`/`PAUSED`/`COMPLETED`/`ABANDONED`), `available_time_per_day`.

## 2. Onboarding & Clarification Protocol

- Ask clarifying questions **only** when missing data materially changes sequencing or feasibility.
- Limit clarification to 2–3 targeted questions max per turn.
- If deadline or availability is missing, Planning Agent emits `status: clarification_needed` instead of guessing.

## 3. Multi-Goal Balancing Priority

When active goals compete for user time, rank strictly by:
`priority` > `deadline proximity` > `urgency signal` > `current progress` > `available time`.

## 4. Output Contract Validation

Planning Agent outputs must be validated against `PlanOutput` or `ClarificationOutput` in `backend/app/schemas/planning.py`. Reject freeform prose or invalid schemas.
