---
name: task_planning
description: Convert goals into milestones, weekly objectives, and concrete daily tasks
purpose: Generates actionable, realistic schedules that respect the user's actual constraints
triggers:
  - planning_agent
  - daily_plan
  - create_tasks
  - schedule
  - task_planning
  - pomodoro_timer
---

## Task Planning Skill

Translates long-term goals into concrete, time-bounded work sessions.

## Task Quality Criteria

Bad task:
> "Study AI"

Good task:
> "Read Chapter 3 of Python for Data Analysis, focusing on pandas groupby. (~45 min)"

Every task must be:
- **Specific** — clear subject matter
- **Time-bounded** — estimated duration in minutes
- **Actionable** — starts with a verb (Read, Write, Solve, Build, Practice)
- **Achievable** — completable in the scheduled slot

## Planning Constraints to Respect

Always ask (once, naturally) for:
1. Available time window (e.g., 4 PM - 10 PM)
2. Fixed commitments within that window (dinner, calls)
3. Preferred break frequency

Then generate the schedule. Never fill every minute — leave buffer for:
- Meals and transitions
- Unexpected interruptions
- Energy dips

## Balancing Multiple Goals

When planning for multiple goals:

1. Sort goals by priority (user-set or inferred from deadline urgency)
2. Allocate time proportionally: higher priority = more time blocks
3. Never schedule the same goal for more than 2 consecutive hours
4. Rotate goals to prevent fatigue

## Adaptive Planning

If skip patterns are detected:

1. Do NOT automatically reschedule
2. Present the observation to the user naturally
3. Ask ONE question: "Would you like to adjust the schedule?"
4. Only update after explicit user approval

## Session Lengths

Default session lengths (adjust based on user preference):
- Study session: 45 minutes
- Practice/coding: 60 minutes
- Review: 20 minutes
- Break: 10-15 minutes
- Light reading: 25 minutes

## Plan Output Format

When presenting a plan, format it as:
```
4:30-5:15  [Python]: Functions and scope — Chapter 4 exercises
5:15-5:30  Break
5:30-6:15  [AI Engineering]: Read about neural network activations
8:00-8:45  [GATE]: Data structures — practice problems set 3
...
```

Always end with: "This is a suggestion — let me know if you'd like to adjust anything."
