---
name: goal_management
description: Create, track, prioritize, and balance multiple concurrent user goals
purpose: Manages the full goal lifecycle without hardcoded user-specific content; works for any goal type
triggers:
  - goal_tracker
  - personal_agent
  - goal
  - create_goal
  - goal_management
---

## Goal Management Skill

This skill governs how JARVIS-X handles user goals of any type.

## Goal Lifecycle

```
Created -> Active -> [Paused | Completed | Abandoned]
                         |
                      Resumed -> Active
```

Transitions:
- **Pause**: User signals deprioritization or temporary block
- **Resume**: User returns to a paused goal
- **Abandon**: User explicitly decides to stop (always ask once to confirm)
- **Complete**: Goal success criteria are met

## Progressive Context Discovery

When a user mentions a new goal:

1. Create the goal immediately (don't wait for all details)
2. Identify the ONE most important missing piece of context
3. Ask naturally — do NOT present a form
4. Save the answer via `goal_tracker update_context`
5. Call `personal_agent` to determine if more context is needed or if a plan can be built
6. When `personal_agent` returns `create_plan`, generate milestones and save via `goal_tracker set_plan`

## Multiple Goals

- The user can have unlimited simultaneous active goals
- Never replace a goal when a new one is created
- Balance goals by priority, deadline, and available time
- Surface all goals in weekly reviews

## Goal Types

This skill works for ANY goal type:
- Exam preparation (GATE, IELTS, GMAT, JEE)
- Career (job search, promotion, career change)
- Learning (Python, AI/ML, language, music)
- Fitness (running, weight, gym)
- Project (JARVIS-X, startup, research)
- Personal (reading, travel, relationship)

Do NOT create a different goal type for each subject — use the metadata fields.

## Metadata to Collect (progressively)

- `target`: deadline or milestone date
- `availability`: hours per day/week available
- `baseline`: current knowledge/skill level
- `motivation`: why this goal matters
- `constraints`: existing commitments, hard blockers
- `scope`: specific subjects or areas to cover

Collect only what is needed. Do not ask for data already in profile or memory.
